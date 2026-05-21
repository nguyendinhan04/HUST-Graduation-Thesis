import logging
import os
import pickle
import re
import sys
from typing import Any

import boto3
from redis import Redis
from rq import Queue, SimpleWorker
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _get_database_url() -> str:
    user = os.getenv("PG_USER", "airflow")
    password = os.getenv("PG_PASSWORD", "airflow")
    host = os.getenv("PG_HOST", "postgres")
    port = os.getenv("PG_PORT", "5432")
    database = os.getenv("PG_DATABASE", "job_db_2")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


engine = create_engine(_get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "y"}


def load_tfidf_artifacts_from_minio() -> dict[str, Any]:
    endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "ROOTUSER")
    secret_key = os.getenv("MINIO_SECRET_KEY", "1234567890")
    bucket_name = os.getenv("MINIO_BUCKET", "models")
    secure = _env_bool("MINIO_SECURE", False)
    model_key = os.getenv("TFIDF_MODEL_KEY")
    prefix = os.getenv("TFIDF_MODEL_PREFIX", "models/tfidf/")

    s3_client = boto3.client(
        "s3",
        endpoint_url=f"http{'s' if secure else ''}://{endpoint}",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
    )

    if not model_key:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        objects = response.get("Contents", [])
        if not objects:
            raise FileNotFoundError(f"Không tìm thấy TF-IDF artifact trong s3://{bucket_name}/{prefix}")
        model_key = max(objects, key=lambda obj: obj["LastModified"])["Key"]

    obj = s3_client.get_object(Bucket=bucket_name, Key=model_key)
    artifacts = pickle.loads(obj["Body"].read())

    for key in ("vectorizer", "svd"):
        if key not in artifacts:
            raise KeyError(f"TF-IDF artifact thiếu key bắt buộc: {key}")

    logger.info("Đã tải TF-IDF artifact từ MinIO: s3://%s/%s", bucket_name, model_key)
    return artifacts


logger.info("Đang tải TF-IDF vectorizer và SVD artifacts...")
try:
    tfidf_artifacts = load_tfidf_artifacts_from_minio()
    vectorizer = tfidf_artifacts["vectorizer"]
    svd = tfidf_artifacts["svd"]
    logger.info("Đã tải TF-IDF vectorizer và SVD thành công.")
except Exception as e:
    logger.error("Lỗi khi tải TF-IDF artifacts: %s", e)
    sys.exit(1)


def clean_text(text: str) -> str:
    text = str(text or "").lower()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def normalize_to_list(value: Any) -> list[Any]:
    if not value:
        return []
    return value if isinstance(value, list) else [value]


def append_if_exists(combined_parts: list[str], item: dict[str, Any], keys: list[str]) -> None:
    for key in keys:
        value = item.get(key)
        if not value:
            continue

        if isinstance(value, list):
            combined_parts.append(" ".join(map(str, value)))
        else:
            combined_parts.append(str(value))


def append_weighted_if_exists(
    combined_parts: list[str],
    item: dict[str, Any],
    keys: list[str],
    weight: int = 2,
) -> None:
    for key in keys:
        value = item.get(key)
        if not value:
            continue

        text = " ".join(map(str, value)) if isinstance(value, list) else str(value)
        combined_parts.extend([text] * weight)


def build_profile_query_text(profile: dict[str, Any]) -> str:
    combined_parts: list[str] = []

    educations = normalize_to_list(
        profile.get("Educations")
        or profile.get("educations")
        or profile.get("Education")
        or profile.get("education")
    )
    for edu in educations:
        if isinstance(edu, dict):
            append_if_exists(
                combined_parts,
                edu,
                [
                    "Field of study",
                    "Field of Study",
                    "field_of_study",
                    "Major",
                    "major",
                    "Degree",
                    "degree",
                    "Description",
                    "description",
                ],
            )
            append_weighted_if_exists(
                combined_parts,
                edu,
                ["Skill", "skill", "Skills", "skills"],
                weight=2,
            )
        elif edu:
            combined_parts.append(str(edu))

    experiences = normalize_to_list(
        profile.get("Experiences")
        or profile.get("experiences")
        or profile.get("Experience")
        or profile.get("experience")
    )
    for exp in experiences:
        if isinstance(exp, dict):
            append_if_exists(
                combined_parts,
                exp,
                [
                    "Position",
                    "position",
                    "Company name",
                    "company_name",
                    "Description",
                    "description",
                ],
            )
            append_weighted_if_exists(combined_parts, exp, ["Title", "title"], weight=2)
            append_weighted_if_exists(
                combined_parts,
                exp,
                ["Skill", "skill", "Skills", "skills"],
                weight=2,
            )
        elif exp:
            combined_parts.append(str(exp))

    profile_skills = profile.get("Skills") or profile.get("skills")
    if profile_skills:
        if isinstance(profile_skills, list):
            combined_parts.extend([" ".join(map(str, profile_skills))] * 2)
        else:
            combined_parts.extend([str(profile_skills)] * 2)

    return " ".join(combined_parts)


def vectorize_tfidf_text(text: str) -> list[float]:
    query_clean = clean_text(text)
    query_tfidf = vectorizer.transform([query_clean])
    query_vector = svd.transform(query_tfidf)[0]
    return query_vector.tolist()


def to_pgvector_literal(vector: Any) -> str:
    if hasattr(vector, "tolist"):
        vector = vector.tolist()

    flattened = []
    for value in vector:
        flattened.append(str(float(value)))
    return "[" + ",".join(flattened) + "]"


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


def upsert_user_profile_tfidf_embedding(
    employee_id: int,
    profile_vector: list[float],
) -> None:
    vector_tfidf = to_pgvector_literal(profile_vector)

    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                INSERT INTO user_profile_embedding (
                    employee_id,
                    vector_tfidf
                )
                VALUES (
                    :employee_id,
                    CAST(:vector_tfidf AS vector)
                )
                ON CONFLICT (employee_id) DO UPDATE
                SET vector_tfidf = EXCLUDED.vector_tfidf
                """
            ),
            {
                "employee_id": employee_id,
                "vector_tfidf": vector_tfidf,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def process_user_profile_tfidf_task(profile: dict[str, Any]) -> list[float]:
    """
    Task chạy ngầm trên Worker RQ.
    Nhận user profile, gộp education/experience/skills, trả về vector TF-IDF + SVD.
    """
    query_text = build_profile_query_text(profile)
    if not clean_text(query_text):
        logger.info("Bỏ qua TF-IDF vector vì user profile rỗng.")
        return []

    logger.info("Đang tính TF-IDF vector cho user profile, query length=%s", len(query_text))
    return vectorize_tfidf_text(query_text)


def process_user_profile_tfidf_update_task(payload: dict[str, Any]) -> dict[str, Any]:
    user_id = int(payload["user_id"])
    employee_id = int(payload["employee_id"])
    profile = payload["profile"]
    lock_key = f"user:{user_id}:tfidf_embedding_lock"

    redis_conn = get_redis_connection()
    lock = redis_conn.lock(
        lock_key,
        timeout=int(os.getenv("TFIDF_EMBEDDING_LOCK_TIMEOUT", 600)),
        blocking_timeout=int(os.getenv("TFIDF_EMBEDDING_LOCK_BLOCKING_TIMEOUT", 600)),
    )

    logger.info("Đang xử lý TF-IDF update task user_id=%s", user_id)
    with lock:
        profile_vector = process_user_profile_tfidf_task(profile)
        vector_size = len(profile_vector)
        if vector_size == 0:
            logger.info("Không cập nhật TF-IDF vector user_id=%s vì profile rỗng.", user_id)
            return {
                "user_id": user_id,
                "employee_id": employee_id,
                "vector_tfidf_updated": False,
                "vector_size": 0,
                "status": "skipped",
                "reason": "empty_profile",
            }

        upsert_user_profile_tfidf_embedding(
            employee_id=employee_id,
            profile_vector=profile_vector,
        )

    logger.info("Đã cập nhật TF-IDF vector user_id=%s, vector_size=%s", user_id, vector_size)
    return {
        "user_id": user_id,
        "employee_id": employee_id,
        "vector_tfidf_updated": True,
        "vector_size": vector_size,
    }


def embed_tfidf_texts_task(texts: list[str]) -> list[list[float]]:
    """
    Task chạy ngầm trên Worker RQ.
    Nhận danh sách text đã gộp, trả về danh sách vector TF-IDF + SVD.
    """
    if not texts:
        return []

    logger.info("Đang tính TF-IDF vectors cho %s texts", len(texts))
    return [vectorize_tfidf_text(text) for text in texts]


if __name__ == "__main__":
    queue_name = os.getenv("QUEUE_NAME", "skill-embedding-queue")
    logger.info("Khởi động TF-IDF Worker. Đang lắng nghe trên queue '%s'...", queue_name)

    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_password = os.getenv("REDIS_PASSWORD", None)
    redis_db = int(os.getenv("REDIS_DB", 0))
    worker_name = os.getenv("WORKER_NAME", "tfidf_worker")

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
