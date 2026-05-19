import os
import sys
import logging
import re
from typing import List

import numpy as np
from redis import Redis
from rq import Queue, Worker
from sentence_transformers import SentenceTransformer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

PROFILE_VECTOR_SIZE = 384

logger.info("Đang tải mô hình Hugging Face 'alvperez/skill-sim-model'...")
try:
    # Load model ONCE when worker starts up into memory (Global caching)
    skill_model = SentenceTransformer("alvperez/skill-sim-model")
    logger.info("Đã tải skill embedding model thành công.")
except Exception as e:
    logger.error(f"Lỗi khi tải skill embedding model: {e}")
    sys.exit(1)

logger.info("Đang tải mô hình Hugging Face 'paraphrase-multilingual-MiniLM-L12-v2'...")
try:
    # Load model ONCE in worker, not in FastAPI.
    bert_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    logger.info("Đã tải BERT/MiniLM model thành công.")
except Exception as e:
    logger.error(f"Lỗi khi tải BERT/MiniLM model: {e}")
    sys.exit(1)


def embed_skills_task(skill_names: List[str]) -> List[List[float]]:
    """
    Task chạy ngầm trên Worker RQ.
    Nhận mảng tên kỹ năng, trả về mảng các vector đã tính toán.
    """
    if not skill_names:
        return []
        
    logger.info(f"Đang tính toán embeddings cho {len(skill_names)} skills: {skill_names}")
    embeddings = skill_model.encode(skill_names)
    
    # Conver Numpy Array -> Python list of floats để JSON serializable (cho Redis RQ)
    embeddings_list = [emb.tolist() for emb in embeddings]
    
    logger.info("Đã tính toán thành công.")
    return embeddings_list


def embed_bert_texts_task(texts: List[str]) -> List[List[float]]:
    """
    Task chạy ngầm trên Worker RQ.
    Nhận mảng text ngắn, trả về MiniLM embeddings cho BERT flow.
    """
    if not texts:
        return []

    logger.info(f"Đang tính toán BERT/MiniLM embeddings cho {len(texts)} texts")
    embeddings = bert_model.encode(texts)
    embeddings_list = [emb.tolist() for emb in embeddings]

    logger.info("Đã tính toán BERT/MiniLM embeddings thành công.")
    return embeddings_list


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def calculate_recency_weight(end_time_str, current_year=2026):
    if not end_time_str or str(end_time_str).lower() in ["hiện tại", "nay", "now", "present"]:
        return 1.0

    try:
        years = re.findall(r"\d{4}", str(end_time_str))
        if years:
            end_year = int(years[-1])
            diff = current_year - end_year
            return max(0.3, 0.8 ** diff)
    except Exception:
        pass

    return 0.5


def as_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    return [value]


def embed_bert_document(text: str, max_words_per_chunk: int = 300) -> np.ndarray:
    words = (text or "").split()
    chunks = [
        " ".join(words[i:i + max_words_per_chunk])
        for i in range(0, len(words), max_words_per_chunk)
    ]
    if not chunks:
        chunks = [""]

    chunk_embeddings = bert_model.encode(chunks)
    doc_embedding = np.mean(chunk_embeddings, axis=0)
    norm = np.linalg.norm(doc_embedding)
    if norm > 0:
        doc_embedding = doc_embedding / norm

    return doc_embedding


def embed_bert_documents_task(
    texts: List[str],
    max_words_per_chunk: int = 300,
) -> List[List[float]]:
    """
    Task chạy ngầm trên Worker RQ.
    Mean-pool MiniLM embeddings theo chunks để embed document dài.
    """
    if not texts:
        return []

    logger.info(f"Đang tính toán BERT/MiniLM document embeddings cho {len(texts)} documents")
    document_embeddings = []

    for text in texts:
        document_embeddings.append(
            embed_bert_document(text, max_words_per_chunk).tolist()
        )

    logger.info("Đã tính toán BERT/MiniLM document embeddings thành công.")
    return document_embeddings


def embed_bert_experience_task(experience: dict) -> List[float]:
    """
    Task chạy ngầm trên Worker RQ.
    Nhận một experience, trả về MiniLM embedding cho experience đó.
    """
    logger.info("Đang tính toán BERT/MiniLM embedding cho một experience")
    experience_text = clean_text(
        f"{experience.get('Title', '')} "
        f"{experience.get('Description', '')} "
        f"{experience.get('skill', '')}"
    )
    embedding = embed_bert_document(experience_text)
    logger.info("Đã tính toán BERT/MiniLM experience embedding thành công.")
    return embedding.tolist()


def embed_bert_education_task(education: dict) -> List[float]:
    """
    Task chạy ngầm trên Worker RQ.
    Nhận một education, trả về MiniLM embedding cho education đó.
    """
    logger.info("Đang tính toán BERT/MiniLM embedding cho một education")
    education_text = clean_text(
        f"{education.get('Field of study', '')} "
        f"{education.get('Skill', '')} "
        f"{education.get('Description', '')}"
    )
    embedding = embed_bert_document(education_text)
    logger.info("Đã tính toán BERT/MiniLM education embedding thành công.")
    return embedding.tolist()


def process_user_profile_multimodal_task(profile: dict) -> dict:
    """
    Task chạy ngầm trên Worker RQ.
    Tính experience_vec và education_vec cho user profile bằng MiniLM.
    """
    logger.info("Đang tính toán user profile vectors bằng BERT/MiniLM")

    exp_vec = np.zeros(PROFILE_VECTOR_SIZE)
    total_exp_weight = 0
    for exp in as_list(profile.get("Experiences") or profile.get("experiences")):
        exp_text = clean_text(
            f"{exp.get('Title', '')} {exp.get('Description', '')} {exp.get('skill', '')}"
        )
        weight = calculate_recency_weight(exp.get("Start-end time", ""))
        exp_vec += embed_bert_document(exp_text) * weight
        total_exp_weight += weight

    if total_exp_weight > 0:
        exp_vec = exp_vec / total_exp_weight
        norm = np.linalg.norm(exp_vec)
        if norm > 0:
            exp_vec = exp_vec / norm

    edu_vec = np.zeros(PROFILE_VECTOR_SIZE)
    edu_vecs = []
    for edu in as_list(profile.get("Education") or profile.get("educations")):
        edu_text = clean_text(
            f"{edu.get('Field of study', '')} {edu.get('Skill', '')} {edu.get('Description', '')}"
        )
        edu_vecs.append(embed_bert_document(edu_text))

    if edu_vecs:
        edu_vec = np.mean(edu_vecs, axis=0)
        norm = np.linalg.norm(edu_vec)
        if norm > 0:
            edu_vec = edu_vec / norm

    logger.info("Đã tính toán user profile vectors thành công.")
    return {
        "experience_vec_384": exp_vec.tolist(),
        "education_vec_384": edu_vec.tolist(),
    }


if __name__ == "__main__":
    queue_name = os.getenv("QUEUE_NAME", "skill-embedding-queue")
    logger.info(f"Khởi động Skill Worker. Đang lắng nghe trên queue '{queue_name}'...")

    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_password = os.getenv("REDIS_PASSWORD", None)
    redis_db = int(os.getenv("REDIS_DB", 0))
    worker_name = os.getenv("WORKER_NAME", "skill_embedding_worker")

    redis_conn = Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password,
        decode_responses=False,
        socket_keepalive=True,
        health_check_interval=30,
    )
    worker = Worker(
        [Queue(queue_name, connection=redis_conn)],
        connection=redis_conn,
        name=worker_name,
        log_job_description=True,
        job_monitoring_interval=5,
    )
    worker.work(burst=False, with_scheduler=True)
