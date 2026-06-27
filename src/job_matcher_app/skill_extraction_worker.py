import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

import boto3
import numpy as np
from redis import Redis
from rq import Queue, SimpleWorker
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from job_matcher_app.outbox import ensure_task_outbox_table, run_with_outbox
from job_matcher_app.skill_extraction.skill_repo_base import SkillRepository
from job_matcher_app.skill_extraction.skill_repo_factory import create_skill_repository
from job_matcher_app.skill_extraction.skill_trie import SkillTrie


import json
from functools import lru_cache

@lru_cache(maxsize=1)
def get_telemetry_redis_client():
    from redis import Redis
    return Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        password=os.getenv("REDIS_PASSWORD", None),
        decode_responses=True,
    )

def emit_ner_telemetry(payload: dict):
    try:
        rc = get_telemetry_redis_client()
        stream_name = os.getenv("TELEMETRY_STREAM_NAME", "ner_telemetry_stream")
        str_payload = {k: str(v) for k, v in payload.items()}
        rc.xadd(stream_name, str_payload)
    except Exception as e:
        logger.error(f"Failed to emit telemetry: {e}")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

VALID_EXTRACTOR_MODES = {"ner_skilltrie", "skilltrie_only"}
DEFAULT_NER_MODEL_PREFIX = "models/checkpoint-360/"
DEFAULT_MODEL_CACHE_DIR = "/tmp/job_matcher_models"
NER_LABELS = ["O", "B-SKILL", "I-SKILL"]
DEFAULT_SKILL_SEMANTIC_MODEL = "alvperez/skill-sim-model"
SHORT_SKILL_WHITELIST = {"go", "r", "c", "c#", "c++", ".net", "ui", "ux", "sql", "k8s", "ci/cd"}


def _get_database_url() -> str:
    user = os.getenv("PG_USER", "airflow")
    password = os.getenv("PG_PASSWORD", "airflow")
    host = os.getenv("PG_HOST", "postgres2")
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


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


def get_s3_client():
    endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "ROOTUSER")
    secret_key = os.getenv("MINIO_SECRET_KEY", "1234567890")
    secure = _env_bool("MINIO_SECURE", False)

    return boto3.client(
        "s3",
        endpoint_url=f"http{'s' if secure else ''}://{endpoint}",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
    )


def download_minio_prefix(prefix: str, local_dir: Path) -> Path:
    bucket_name = os.getenv("MINIO_BUCKET", "models")
    prefix = prefix.lstrip("/")
    if prefix and not prefix.endswith("/"):
        prefix = f"{prefix}/"

    local_dir.mkdir(parents=True, exist_ok=True)
    s3_client = get_s3_client()
    paginator = s3_client.get_paginator("list_objects_v2")
    object_count = 0

    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue

            relative_path = key[len(prefix) :] if key.startswith(prefix) else Path(key).name
            target_path = local_dir / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            s3_client.download_file(bucket_name, key, str(target_path))
            object_count += 1

    if object_count == 0:
        raise FileNotFoundError(f"No model files found in s3://{bucket_name}/{prefix}")

    logger.info("Downloaded %s files from s3://%s/%s", object_count, bucket_name, prefix)
    return local_dir


def load_ner_pipeline():
    from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

    cache_dir = Path(os.getenv("MODEL_CACHE_DIR", DEFAULT_MODEL_CACHE_DIR))
    model_prefix = os.getenv("NER_MODEL_PREFIX", DEFAULT_NER_MODEL_PREFIX)
    model_dir = Path(os.getenv("NER_LOCAL_PATH", str(cache_dir / "checkpoint-360")))

    if not model_dir.exists() or not any(model_dir.iterdir()):
        download_minio_prefix(model_prefix, model_dir)

    id2label = {index: label for index, label in enumerate(NER_LABELS)}
    label2id = {label: index for index, label in id2label.items()}
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForTokenClassification.from_pretrained(
        str(model_dir),
        id2label=id2label,
        label2id=label2id,
    )
    device = _env_int("NER_DEVICE", -1)
    logger.info("Loading NER pipeline from %s with device=%s", model_dir, device)
    return pipeline(
        "token-classification",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="max",
        device=device,
    )


def build_skill_trie() -> SkillTrie:
    repo: SkillRepository = create_skill_repository(
        backend="postgres",
        sqlite_db_path=os.getenv("SKILL_SQLITE_DB_PATH", "data/sqlite/skills.db"),
        postgres_host=os.getenv("PG_HOST", "postgres2"),
        postgres_port=os.getenv("PG_PORT", "5432"),
        postgres_database=os.getenv("PG_DATABASE", "job_db_2"),
        postgres_user=os.getenv("PG_USER", "airflow"),
        postgres_password=os.getenv("PG_PASSWORD", "airflow"),
        postgres_schema=os.getenv("SKILL_REPO_SCHEMA", "public"),
    )
    repo.init_schema()

    skills = repo.list_skills()
    trie = SkillTrie()
    trie.add_many([(skill.name, skill.synonyms) for skill in skills])
    logger.info(
        "Loaded SkillTrie with %s skills and %s keywords",
        trie.skill_count(),
        trie.keyword_count(),
    )
    return trie


def parse_pgvector_text(vector_text: str) -> list[float]:
    return [
        float(value)
        for value in str(vector_text).strip("[]").split(",")
        if value.strip()
    ]


def l2_normalize(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype="float32")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def load_skill_embedding_index() -> dict[str, Any]:
    db = SessionLocal()
    try:
        rows = db.execute(
            text(
                """
                SELECT
                    s.id AS skill_id,
                    s.name AS skill_name,
                    se.embedding::text AS embedding
                FROM skills s
                JOIN skill_embeddings se ON se.skill_id = s.id
                ORDER BY s.name ASC
                """
            )
        ).mappings().all()
    finally:
        db.close()

    if not rows:
        raise ValueError("skill_embeddings is empty. Generate skill embeddings before starting worker.")

    skill_ids = [int(row["skill_id"]) for row in rows]
    skill_names = [str(row["skill_name"]) for row in rows]
    matrix = np.asarray(
        [parse_pgvector_text(str(row["embedding"])) for row in rows],
        dtype="float32",
    )
    if matrix.ndim != 2 or matrix.shape[0] != len(skill_names):
        raise ValueError(f"Invalid skill embedding matrix shape: {matrix.shape}")

    matrix = l2_normalize(matrix)
    logger.info(
        "Loaded %s skill embeddings with dimension=%s",
        len(skill_names),
        matrix.shape[1],
    )
    return {
        "skill_ids": skill_ids,
        "skill_names": skill_names,
        "matrix": matrix,
    }


def load_skill_semantic_model():
    from sentence_transformers import SentenceTransformer

    model_name = os.getenv("SKILL_SEMANTIC_MODEL", DEFAULT_SKILL_SEMANTIC_MODEL)
    logger.info("Loading skill semantic model: %s", model_name)
    return SentenceTransformer(model_name)


def normalize_skill_name(value: Any) -> str:
    text_value = str(value or "")
    text_value = text_value.replace("##", "")
    text_value = text_value.replace("_", " ")
    text_value = text_value.replace("▁", " ")
    text_value = re.sub(r"\s+", " ", text_value).strip(" \t\r\n.,;:/\\|()[]{}-")
    return text_value


def is_supported_ner_entity(entity_group: str) -> bool:
    return "SKILL" in entity_group


def reject_ner_phrase(raw_phrase: Any, normalized_phrase: str, score: float) -> str | None:
    raw_text = str(raw_phrase or "").strip()
    phrase = normalize_skill_name(normalized_phrase)
    key = phrase.casefold()

    if not phrase:
        return "empty"
    if score < _env_float("NER_SCORE_THRESHOLD", 0.75):
        return "low_score"
    if key in SHORT_SKILL_WHITELIST:
        return None
    if raw_text.startswith("-") or raw_text.endswith("-"):
        return "dash_fragment"
    if phrase.startswith("-") or phrase.endswith("-"):
        return "dash_fragment"
    if len(phrase) <= 3:
        return "too_short"
    return None


def unique_skill_names(skill_names: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for skill_name in skill_names:
        cleaned = normalize_skill_name(skill_name)
        if not cleaned:
            continue

        key = cleaned.lower()
        if key in seen:
            continue

        seen.add(key)
        normalized.append(cleaned)

    return normalized


def build_job_text(job: dict[str, Any]) -> str:
    parts = [
        job.get("title") or job.get("job_title") or "",
        job.get("description") or "",
        job.get("requirement") or "",
    ]
    text_value = " ".join(str(part) for part in parts if part)
    text_value = re.sub(r"<[^>]+>", " ", text_value)
    return re.sub(r"\s+", " ", text_value).strip()


def extract_ner_candidates(text_value: str) -> tuple[list[str], dict[str, int]]:
    if ner_pipeline is None or not text_value:
        return [], {"raw": 0, "accepted": 0, "rejected": 0}

    max_chars = _env_int("NER_MAX_CHARS", 4000)
    predictions = ner_pipeline(text_value[:max_chars])
    candidates: list[str] = []
    raw_count = 0
    rejected_count = 0
    seen: set[str] = set()

    for prediction in predictions:
        entity_group = str(prediction.get("entity_group", ""))
        raw_count += 1
        if not is_supported_ner_entity(entity_group):
            rejected_count += 1
            continue

        raw_phrase = prediction.get("word", "")
        phrase = normalize_skill_name(raw_phrase)
        score = float(prediction.get("score") or 0.0)
        reject_reason = reject_ner_phrase(raw_phrase, phrase, score)
        if reject_reason:
            rejected_count += 1
            logger.debug(
                "Rejected NER candidate phrase=%r score=%.4f reason=%s",
                raw_phrase,
                score,
                reject_reason,
            )
            continue

        key = phrase.casefold()
        if key in seen:
            rejected_count += 1
            continue
        seen.add(key)
        candidates.append(phrase)

    return candidates, {
        "raw": raw_count,
        "accepted": len(candidates),
        "rejected": rejected_count,
    }


def semantic_normalize_ner_candidates(candidate_phrases: list[str]) -> list[str]:
    if not candidate_phrases:
        return []
    if skill_semantic_model is None or skill_embedding_index is None:
        raise RuntimeError("Semantic skill model and skill embeddings must be loaded")

    phrases = unique_skill_names(candidate_phrases)
    phrase_embeddings = skill_semantic_model.encode(
        phrases,
        batch_size=_env_int("NER_SEMANTIC_BATCH_SIZE", 64),
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype("float32")

    matrix = skill_embedding_index["matrix"]
    skill_names = skill_embedding_index["skill_names"]
    threshold = _env_float("NER_SEMANTIC_THRESHOLD", 0.70)
    scores = phrase_embeddings @ matrix.T

    normalized_skills: list[str] = []
    for phrase, phrase_scores in zip(phrases, scores):
        best_index = int(np.argmax(phrase_scores))
        best_score = float(phrase_scores[best_index])
        if best_score < threshold:
            logger.debug(
                "Dropped NER candidate phrase=%r semantic_score=%.4f threshold=%.4f",
                phrase,
                best_score,
                threshold,
            )
            continue

        skill_name = str(skill_names[best_index])
        normalized_skills.append(skill_name)
        logger.debug(
            "Normalized NER candidate phrase=%r -> skill=%r score=%.4f",
            phrase,
            skill_name,
            best_score,
        )

    return unique_skill_names(normalized_skills)


def extract_skills_with_skilltrie(text_value: str) -> list[str]:
    if skill_trie is None or not text_value:
        return []
    return unique_skill_names(skill_trie.extract(text_value))


def extract_job_skills(job: dict[str, Any]) -> tuple[list[str], str]:
    text_value = build_job_text(job)
    if not text_value:
        return [], extractor_mode

    skilltrie_skills = extract_skills_with_skilltrie(text_value)
    if extractor_mode == "skilltrie_only":
        return skilltrie_skills, "skilltrie_only"

    ner_candidates, ner_stats = extract_ner_candidates(text_value)
    
    skilltrie_set = set(skilltrie_skills)
    intersected_skills = [s for s in ner_candidates if s in skilltrie_set]
    final_skills = unique_skill_names(intersected_skills)
    
    dropped_candidates = [s for s in ner_candidates if s not in skilltrie_set]
    job_id = job.get("id") or job.get("job_id") or 0
    for dropped in dropped_candidates:
        emit_ner_telemetry({
            "job_id": job_id,
            "raw_text": text_value,
            "ner_phrase": dropped,
            "status": "dropped_not_in_trie"
        })
        
    logger.info(
        "Skill extraction candidates: skilltrie=%s ner_raw=%s ner_accepted=%s "
        "ner_rejected=%s final=%s",
        len(skilltrie_skills),
        ner_stats["raw"],
        ner_stats["accepted"],
        ner_stats["rejected"],
        len(final_skills),
    )
    return final_skills, "skilltrie_ner"


def replace_job_skills(job_id: int, skill_names: list[str]) -> dict[str, Any]:
    db = SessionLocal()
    try:
        existing_job = db.execute(
            text("SELECT id FROM jobs WHERE id = :job_id"),
            {"job_id": job_id},
        ).first()
        if existing_job is None:
            raise ValueError(f"Job with id {job_id} not found")

        normalized_names = unique_skill_names(skill_names)
        skill_rows: list[dict[str, Any]] = []

        if normalized_names:
            lower_names = [name.lower() for name in normalized_names]
            rows = db.execute(
                text(
                    """
                    SELECT id, name
                    FROM skills
                    WHERE lower(name) = ANY(:lower_names)
                    """
                ),
                {"lower_names": lower_names},
            ).mappings().all()
            skills_by_key = {row["name"].lower(): dict(row) for row in rows}

            for skill_name in normalized_names:
                key = skill_name.lower()
                if key not in skills_by_key:
                    row = db.execute(
                        text(
                            """
                            INSERT INTO skills (name, embedding_status)
                            VALUES (:name, 'pending')
                            RETURNING id, name
                            """
                        ),
                        {"name": skill_name},
                    ).mappings().one()
                    skills_by_key[key] = dict(row)

                skill_rows.append(skills_by_key[key])

        db.execute(
            text("DELETE FROM job_skills WHERE job_id = :job_id"),
            {"job_id": job_id},
        )

        for skill in skill_rows:
            db.execute(
                text(
                    """
                    INSERT INTO job_skills (job_id, skill_id, is_required)
                    VALUES (:job_id, :skill_id, true)
                    """
                ),
                {
                    "job_id": job_id,
                    "skill_id": skill["id"],
                },
            )

        db.commit()
        return {
            "job_id": job_id,
            "skill_count": len(skill_rows),
            "skills": [
                {
                    "skill_id": skill["id"],
                    "skill_name": skill["name"],
                    "is_required": True,
                }
                for skill in skill_rows
            ],
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def process_job_skill_extraction_task(payload: dict[str, Any]) -> dict[str, Any]:
    def _process() -> dict[str, Any]:
        job_id = int(payload.get("job_id") or 0)
        job = payload.get("job") or {}
        if not job_id:
            raise ValueError("job_id is required")
        if not isinstance(job, dict):
            raise ValueError("job payload must be an object")

        skill_names, extraction_source = extract_job_skills(job)
        result = replace_job_skills(job_id, skill_names)
        result.update(
            {
                "extraction_source": extraction_source,
                "extractor_mode": extractor_mode,
            }
        )
        logger.info(
            "Extracted %s skills for job_id=%s using %s",
            result["skill_count"],
            job_id,
            extraction_source,
        )
        return result

    return run_with_outbox(payload, _process)


extractor_mode = os.getenv("SKILL_EXTRACTOR_MODE", "ner_skilltrie").strip().lower()
if extractor_mode not in VALID_EXTRACTOR_MODES:
    logger.error(
        "Invalid SKILL_EXTRACTOR_MODE=%s. Expected one of: %s",
        extractor_mode,
        ", ".join(sorted(VALID_EXTRACTOR_MODES)),
    )
    sys.exit(1)

logger.info("Starting skill extraction worker with mode=%s", extractor_mode)
try:
    skill_trie = build_skill_trie()
except Exception as exc:
    logger.error("Failed to build SkillTrie: %s", exc)
    sys.exit(1)

ner_pipeline = None
skill_semantic_model = None
skill_embedding_index = None
if extractor_mode == "ner_skilltrie":
    try:
        ner_pipeline = load_ner_pipeline()
        skill_semantic_model = load_skill_semantic_model()
        skill_embedding_index = load_skill_embedding_index()
    except Exception as exc:
        logger.error("Failed to load NER/semantic extraction dependencies: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    queue_name = os.getenv("QUEUE_NAME", "job-skill-extraction-queue")
    worker_name = os.getenv("WORKER_NAME", "job_skill_extraction_worker")
    ensure_task_outbox_table()

    redis_conn = Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        password=os.getenv("REDIS_PASSWORD", None),
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
    logger.info("Listening on queue '%s'", queue_name)
    worker.work(burst=False, with_scheduler=True)
