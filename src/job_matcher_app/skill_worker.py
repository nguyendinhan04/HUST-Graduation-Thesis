import os
import sys
import logging
import re
from typing import List

import numpy as np
from redis import Redis
from rq import Queue, SimpleWorker
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

PROFILE_VECTOR_SIZE = 384


def _get_database_url() -> str:
    user = os.getenv("PG_USER", "airflow")
    password = os.getenv("PG_PASSWORD", "airflow")
    host = os.getenv("PG_HOST", "postgres")
    port = os.getenv("PG_PORT", "5432")
    database = os.getenv("PG_DATABASE", "job_db_2")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


engine = create_engine(_get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

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


def to_pgvector_literal(vector) -> str:
    if hasattr(vector, "tolist"):
        vector = vector.tolist()

    vector = np.asarray(vector).reshape(-1)
    return "[" + ",".join(str(float(value)) for value in vector) + "]"


def parse_pgvector_text(vector_text: str) -> List[float]:
    return [
        float(value)
        for value in vector_text.strip("[]").split(",")
        if value.strip()
    ]


def get_redis_connection() -> Redis:
    return Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        password=os.getenv("REDIS_PASSWORD", None),
        decode_responses=False,
        socket_keepalive=True,
        health_check_interval=30,
    )


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


def ensure_and_lock_profile_embedding_row(db, employee_id: int) -> None:
    db.execute(
        text(
            """
            INSERT INTO user_profile_embedding (employee_id)
            VALUES (:employee_id)
            ON CONFLICT (employee_id) DO NOTHING
            """
        ),
        {"employee_id": employee_id},
    )
    db.execute(
        text(
            """
            SELECT employee_id
            FROM user_profile_embedding
            WHERE employee_id = :employee_id
            FOR UPDATE
            """
        ),
        {"employee_id": employee_id},
    )


def recompute_profile_education_vector(db, employee_id: int) -> None:
    result = db.execute(
        text(
            """
            SELECT
                education_id,
                education_vec::text AS education_vec
            FROM employee_education_embedding
            WHERE employee_id = :employee_id
              AND education_vec IS NOT NULL
            """
        ),
        {"employee_id": employee_id},
    )
    rows = result.fetchall()

    if not rows:
        db.execute(
            text(
                """
                UPDATE user_profile_embedding
                SET education_vec = NULL
                WHERE employee_id = :employee_id
                """
            ),
            {"employee_id": employee_id},
        )
        return

    education_vectors = []
    for row in rows:
        vector = np.asarray(parse_pgvector_text(row.education_vec), dtype=float)
        if vector.size != PROFILE_VECTOR_SIZE:
            raise ValueError(
                f"Education vector for education_id {row.education_id} "
                f"has size {vector.size}, expected {PROFILE_VECTOR_SIZE}"
            )
        education_vectors.append(vector)

    aggregate_vec = np.mean(education_vectors, axis=0)
    norm = np.linalg.norm(aggregate_vec)
    if norm > 0:
        aggregate_vec = aggregate_vec / norm

    db.execute(
        text(
            """
            UPDATE user_profile_embedding
            SET education_vec = CAST(:education_vec AS vector)
            WHERE employee_id = :employee_id
            """
        ),
        {
            "employee_id": employee_id,
            "education_vec": to_pgvector_literal(aggregate_vec),
        },
    )


def upsert_education_embedding_and_recompute_profile(
    employee_id: int,
    education_id: int,
    education_vector: List[float],
) -> None:
    education_vector_literal = to_pgvector_literal(education_vector)

    db = SessionLocal()
    try:
        ensure_and_lock_profile_embedding_row(db, employee_id)
        db.execute(
            text(
                """
                INSERT INTO employee_education_embedding (
                    employee_id,
                    education_id,
                    education_vec
                )
                VALUES (
                    :employee_id,
                    :education_id,
                    CAST(:education_vec AS vector)
                )
                ON CONFLICT (education_id) DO UPDATE
                SET employee_id = EXCLUDED.employee_id,
                    education_vec = EXCLUDED.education_vec
                """
            ),
            {
                "employee_id": employee_id,
                "education_id": education_id,
                "education_vec": education_vector_literal,
            },
        )

        recompute_profile_education_vector(db, employee_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def delete_education_embedding_and_recompute_profile(
    employee_id: int,
    education_id: int,
) -> None:
    db = SessionLocal()
    try:
        ensure_and_lock_profile_embedding_row(db, employee_id)
        db.execute(
            text(
                """
                DELETE FROM employee_education_embedding
                WHERE education_id = :education_id
                """
            ),
            {"education_id": education_id},
        )

        recompute_profile_education_vector(db, employee_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def process_user_education_embedding_task(payload: dict) -> dict:
    user_id = int(payload["user_id"])
    employee_id = int(payload["employee_id"])
    education_id = int(payload["education_id"])
    education = payload["education"]
    lock_key = f"user:{user_id}:education_embedding_lock"

    redis_conn = get_redis_connection()
    lock = redis_conn.lock(
        lock_key,
        timeout=int(os.getenv("EDUCATION_EMBEDDING_LOCK_TIMEOUT", 600)),
        blocking_timeout=int(os.getenv("EDUCATION_EMBEDDING_LOCK_BLOCKING_TIMEOUT", 600)),
    )

    logger.info(
        "Đang xử lý education embedding task user_id=%s, education_id=%s",
        user_id,
        education_id,
    )
    with lock:
        education_vector = embed_bert_education_task(education)
        upsert_education_embedding_and_recompute_profile(
            employee_id=employee_id,
            education_id=education_id,
            education_vector=education_vector,
        )

    logger.info(
        "Đã lưu education embedding task user_id=%s, education_id=%s",
        user_id,
        education_id,
    )
    return {
        "user_id": user_id,
        "employee_id": employee_id,
        "education_id": education_id,
        "education_embedding_updated": True,
    }


def process_user_education_delete_task(payload: dict) -> dict:
    user_id = int(payload["user_id"])
    employee_id = int(payload["employee_id"])
    education_id = int(payload["education_id"])
    lock_key = f"user:{user_id}:education_embedding_lock"

    redis_conn = get_redis_connection()
    lock = redis_conn.lock(
        lock_key,
        timeout=int(os.getenv("EDUCATION_EMBEDDING_LOCK_TIMEOUT", 600)),
        blocking_timeout=int(os.getenv("EDUCATION_EMBEDDING_LOCK_BLOCKING_TIMEOUT", 600)),
    )

    logger.info(
        "Đang xử lý education embedding delete task user_id=%s, education_id=%s",
        user_id,
        education_id,
    )
    with lock:
        delete_education_embedding_and_recompute_profile(
            employee_id=employee_id,
            education_id=education_id,
        )

    logger.info(
        "Đã xóa education embedding task user_id=%s, education_id=%s",
        user_id,
        education_id,
    )
    return {
        "user_id": user_id,
        "employee_id": employee_id,
        "education_id": education_id,
        "education_embedding_deleted": True,
    }


def recompute_profile_experience_vector(db, employee_id: int) -> None:
    result = db.execute(
        text(
            """
            SELECT
                e.id AS experience_id,
                e.end_date,
                ebe.experience_vec::text AS experience_vec
            FROM employee_experience_embedding ebe
            JOIN experiences e ON e.id = ebe.experience_id
            WHERE ebe.employee_id = :employee_id
              AND ebe.experience_vec IS NOT NULL
            """
        ),
        {"employee_id": employee_id},
    )
    rows = result.fetchall()

    if not rows:
        db.execute(
            text(
                """
                UPDATE user_profile_embedding
                SET experience_vec = NULL
                WHERE employee_id = :employee_id
                """
            ),
            {"employee_id": employee_id},
        )
        return

    aggregate_vec = np.zeros(PROFILE_VECTOR_SIZE)
    total_weight = 0.0
    for row in rows:
        vector = np.asarray(parse_pgvector_text(row.experience_vec), dtype=float)
        if vector.size != PROFILE_VECTOR_SIZE:
            raise ValueError(
                f"Experience vector for experience_id {row.experience_id} "
                f"has size {vector.size}, expected {PROFILE_VECTOR_SIZE}"
            )

        weight = calculate_recency_weight(row.end_date)
        aggregate_vec += vector * weight
        total_weight += weight

    aggregate_vec = aggregate_vec / total_weight
    norm = np.linalg.norm(aggregate_vec)
    if norm > 0:
        aggregate_vec = aggregate_vec / norm

    db.execute(
        text(
            """
            UPDATE user_profile_embedding
            SET experience_vec = CAST(:experience_vec AS vector)
            WHERE employee_id = :employee_id
            """
        ),
        {
            "employee_id": employee_id,
            "experience_vec": to_pgvector_literal(aggregate_vec),
        },
    )


def upsert_experience_embedding_and_recompute_profile(
    employee_id: int,
    experience_id: int,
    experience_vector: List[float],
) -> None:
    experience_vector_literal = to_pgvector_literal(experience_vector)

    db = SessionLocal()
    try:
        ensure_and_lock_profile_embedding_row(db, employee_id)
        db.execute(
            text(
                """
                INSERT INTO employee_experience_embedding (
                    employee_id,
                    experience_id,
                    experience_vec
                )
                VALUES (
                    :employee_id,
                    :experience_id,
                    CAST(:experience_vec AS vector)
                )
                ON CONFLICT (experience_id) DO UPDATE
                SET employee_id = EXCLUDED.employee_id,
                    experience_vec = EXCLUDED.experience_vec
                """
            ),
            {
                "employee_id": employee_id,
                "experience_id": experience_id,
                "experience_vec": experience_vector_literal,
            },
        )

        recompute_profile_experience_vector(db, employee_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def delete_experience_embedding_and_recompute_profile(
    employee_id: int,
    experience_id: int,
) -> None:
    db = SessionLocal()
    try:
        ensure_and_lock_profile_embedding_row(db, employee_id)
        db.execute(
            text(
                """
                DELETE FROM employee_experience_embedding
                WHERE experience_id = :experience_id
                """
            ),
            {"experience_id": experience_id},
        )

        recompute_profile_experience_vector(db, employee_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def process_user_experience_embedding_task(payload: dict) -> dict:
    user_id = int(payload["user_id"])
    employee_id = int(payload["employee_id"])
    experience_id = int(payload["experience_id"])
    experience = payload["experience"]
    lock_key = f"user:{user_id}:experience_embedding_lock"

    redis_conn = get_redis_connection()
    lock = redis_conn.lock(
        lock_key,
        timeout=int(os.getenv("EXPERIENCE_EMBEDDING_LOCK_TIMEOUT", 600)),
        blocking_timeout=int(os.getenv("EXPERIENCE_EMBEDDING_LOCK_BLOCKING_TIMEOUT", 600)),
    )

    logger.info(
        "Đang xử lý experience embedding task user_id=%s, experience_id=%s",
        user_id,
        experience_id,
    )
    with lock:
        experience_vector = embed_bert_experience_task(experience)
        upsert_experience_embedding_and_recompute_profile(
            employee_id=employee_id,
            experience_id=experience_id,
            experience_vector=experience_vector,
        )

    logger.info(
        "Đã lưu experience embedding task user_id=%s, experience_id=%s",
        user_id,
        experience_id,
    )
    return {
        "user_id": user_id,
        "employee_id": employee_id,
        "experience_id": experience_id,
        "experience_embedding_updated": True,
    }


def process_user_experience_delete_task(payload: dict) -> dict:
    user_id = int(payload["user_id"])
    employee_id = int(payload["employee_id"])
    experience_id = int(payload["experience_id"])
    lock_key = f"user:{user_id}:experience_embedding_lock"

    redis_conn = get_redis_connection()
    lock = redis_conn.lock(
        lock_key,
        timeout=int(os.getenv("EXPERIENCE_EMBEDDING_LOCK_TIMEOUT", 600)),
        blocking_timeout=int(os.getenv("EXPERIENCE_EMBEDDING_LOCK_BLOCKING_TIMEOUT", 600)),
    )

    logger.info(
        "Đang xử lý experience embedding delete task user_id=%s, experience_id=%s",
        user_id,
        experience_id,
    )
    with lock:
        delete_experience_embedding_and_recompute_profile(
            employee_id=employee_id,
            experience_id=experience_id,
        )

    logger.info(
        "Đã xóa experience embedding task user_id=%s, experience_id=%s",
        user_id,
        experience_id,
    )
    return {
        "user_id": user_id,
        "employee_id": employee_id,
        "experience_id": experience_id,
        "experience_embedding_deleted": True,
    }


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
    worker = SimpleWorker(
        [Queue(queue_name, connection=redis_conn)],
        connection=redis_conn,
        name=worker_name,
        log_job_description=True,
        job_monitoring_interval=5,
    )
    worker.work(burst=False, with_scheduler=True)
