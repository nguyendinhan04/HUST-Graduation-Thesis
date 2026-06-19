from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Callable, TypeVar

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker


TASK_OUTBOX_PENDING = "pending"
TASK_OUTBOX_DONE = "done"

OUTBOX_TASK_ROUTES = {
    "experience_embedding_update": (
        "job_matcher_app.skill_worker.process_user_experience_embedding_task",
        "10m",
    ),
    "experience_embedding_delete": (
        "job_matcher_app.skill_worker.process_user_experience_delete_task",
        "10m",
    ),
    "education_embedding_update": (
        "job_matcher_app.skill_worker.process_user_education_embedding_task",
        "10m",
    ),
    "education_embedding_delete": (
        "job_matcher_app.skill_worker.process_user_education_delete_task",
        "10m",
    ),
    "job_bert_embedding_update": (
        "job_matcher_app.skill_worker.process_job_bert_embedding_task",
        "10m",
    ),
    "job_tfidf_embedding_update": (
        "job_matcher_app.skill_worker_tfidf.process_job_tfidf_embedding_task",
        "10m",
    ),
    "job_skill_extraction_update": (
        "job_matcher_app.skill_extraction_worker.process_job_skill_extraction_task",
        "10m",
    ),
    "user_profile_tfidf_update": (
        "job_matcher_app.skill_worker_tfidf.process_user_profile_tfidf_update_task",
        "10m",
    ),
}

_RESULT = TypeVar("_RESULT")
_TASK_OUTBOX_TABLE_ENSURED = False


def _get_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def get_default_max_retries() -> int:
    return _get_int_env("OUTBOX_MAX_RETRIES", 5)


def get_retry_base_delay_seconds() -> int:
    return _get_int_env("OUTBOX_RETRY_BASE_DELAY_SECONDS", 60)


def get_retry_max_delay_seconds() -> int:
    return _get_int_env("OUTBOX_RETRY_MAX_DELAY_SECONDS", 3600)


def _get_database_url() -> str:
    user = os.getenv("PG_USER", "airflow")
    password = os.getenv("PG_PASSWORD", "airflow")
    host = os.getenv("PG_HOST", "postgres2")
    port = os.getenv("PG_PORT", "5432")
    database = os.getenv("PG_DATABASE", "job_db_2")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


@lru_cache(maxsize=1)
def _get_session_factory():
    engine = create_engine(_get_database_url(), pool_pre_ping=True)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False), engine


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _safe_error_message(error: BaseException | str) -> str:
    message = str(error)
    return message[:4000]


def ensure_task_outbox_table() -> None:
    global _TASK_OUTBOX_TABLE_ENSURED

    if _TASK_OUTBOX_TABLE_ENSURED:
        return

    _, engine = _get_session_factory()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS task_outbox (
                    id BIGSERIAL PRIMARY KEY,
                    task_type VARCHAR(100) NOT NULL,
                    aggregate_type VARCHAR(100) NOT NULL,
                    aggregate_id BIGINT NOT NULL,
                    queue_name VARCHAR(255) NOT NULL,
                    rq_job_id VARCHAR(255),
                    status VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (
                            status IN (
                                'pending',
                                'done'
                            )
                        ),
                    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                    result JSONB,
                    error_message TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 5,
                    next_retry_at TIMESTAMP,
                    last_attempt_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    dead_letter_at TIMESTAMP,
                    completed_at TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text("ALTER TABLE task_outbox ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0")
        )
        conn.execute(
            text("ALTER TABLE task_outbox ADD COLUMN IF NOT EXISTS max_retries INTEGER NOT NULL DEFAULT 5")
        )
        conn.execute(
            text("ALTER TABLE task_outbox ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP")
        )
        conn.execute(
            text("ALTER TABLE task_outbox ADD COLUMN IF NOT EXISTS last_attempt_at TIMESTAMP")
        )
        conn.execute(
            text("ALTER TABLE task_outbox ADD COLUMN IF NOT EXISTS dead_letter_at TIMESTAMP")
        )
        conn.execute(
            text("ALTER TABLE task_outbox ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP")
        )
        conn.execute(
            text(
                """
                UPDATE task_outbox
                SET status = 'pending',
                    retry_count = GREATEST(retry_count, max_retries),
                    next_retry_at = NULL,
                    dead_letter_at = COALESCE(dead_letter_at, CURRENT_TIMESTAMP),
                    completed_at = COALESCE(completed_at, CURRENT_TIMESTAMP),
                    updated_at = CURRENT_TIMESTAMP
                WHERE status = 'dead_letter'
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE task_outbox
                SET status = 'pending',
                    updated_at = CURRENT_TIMESTAMP
                WHERE status IN ('enqueued', 'processing', 'failed')
                """
            )
        )
        conn.execute(text("ALTER TABLE task_outbox DROP CONSTRAINT IF EXISTS task_outbox_status_check"))
        conn.execute(text("ALTER TABLE task_outbox DROP CONSTRAINT IF EXISTS ck_task_outbox_status"))
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    ALTER TABLE task_outbox
                    ADD CONSTRAINT ck_task_outbox_status
                    CHECK (
                        status IN (
                            'pending',
                            'done'
                        )
                    );
                EXCEPTION
                    WHEN duplicate_object THEN NULL;
                END $$;
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_task_outbox_status_created_at
                ON task_outbox (status, created_at)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_task_outbox_status_next_retry_at
                ON task_outbox (status, next_retry_at, created_at)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_task_outbox_status_updated_at
                ON task_outbox (status, updated_at)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_task_outbox_rq_job_id
                ON task_outbox (rq_job_id)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_task_outbox_aggregate
                ON task_outbox (aggregate_type, aggregate_id)
                """
            )
        )
    _TASK_OUTBOX_TABLE_ENSURED = True


def reset_task_outbox_schema_cache() -> None:
    global _TASK_OUTBOX_TABLE_ENSURED

    _TASK_OUTBOX_TABLE_ENSURED = False


def create_task_outbox(
    *,
    task_type: str,
    aggregate_type: str,
    aggregate_id: int,
    queue_name: str,
    payload: dict[str, Any],
) -> int:
    SessionLocal, _ = _get_session_factory()
    db = SessionLocal()
    try:
        outbox_id = db.execute(
            text(
                """
                INSERT INTO task_outbox (
                    task_type,
                    aggregate_type,
                    aggregate_id,
                    queue_name,
                    status,
                    max_retries,
                    payload
                )
                VALUES (
                    :task_type,
                    :aggregate_type,
                    :aggregate_id,
                    :queue_name,
                    :status,
                    :max_retries,
                    CAST(:payload AS jsonb)
                )
                RETURNING id
                """
            ),
            {
                "task_type": task_type,
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "queue_name": queue_name,
                "status": TASK_OUTBOX_PENDING,
                "max_retries": get_default_max_retries(),
                "payload": _json_dump(payload),
            },
        ).scalar_one()
        db.commit()
        return int(outbox_id)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def create_task_outbox_in_session(
    db: AsyncSession,
    *,
    task_type: str,
    aggregate_type: str,
    aggregate_id: int,
    queue_name: str,
    payload: dict[str, Any],
) -> int:
    outbox_id = (
        await db.execute(
            text(
                """
                INSERT INTO task_outbox (
                    task_type,
                    aggregate_type,
                    aggregate_id,
                    queue_name,
                    status,
                    max_retries,
                    payload
                )
                VALUES (
                    :task_type,
                    :aggregate_type,
                    :aggregate_id,
                    :queue_name,
                    :status,
                    :max_retries,
                    CAST(:payload AS jsonb)
                )
                RETURNING id
                """
            ),
            {
                "task_type": task_type,
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "queue_name": queue_name,
                "status": TASK_OUTBOX_PENDING,
                "max_retries": get_default_max_retries(),
                "payload": _json_dump(payload),
            },
        )
    ).scalar_one()
    return int(outbox_id)


def mark_task_outbox_enqueued(outbox_id: int | None, rq_job_id: str) -> None:
    if not outbox_id:
        return

    SessionLocal, _ = _get_session_factory()
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE task_outbox
                SET rq_job_id = :rq_job_id,
                    error_message = NULL,
                    next_retry_at = NULL,
                    last_attempt_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :outbox_id
                  AND status <> :done_status
                """
            ),
            {
                "outbox_id": outbox_id,
                "rq_job_id": rq_job_id,
                "done_status": TASK_OUTBOX_DONE,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def mark_task_outbox_done(outbox_id: int | None, result: Any = None) -> None:
    if not outbox_id:
        return

    SessionLocal, _ = _get_session_factory()
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE task_outbox
                SET status = :status,
                    result = CAST(:result AS jsonb),
                    error_message = NULL,
                    next_retry_at = NULL,
                    dead_letter_at = NULL,
                    updated_at = CURRENT_TIMESTAMP,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = :outbox_id
                """
            ),
            {
                "outbox_id": outbox_id,
                "status": TASK_OUTBOX_DONE,
                "result": _json_dump(result if result is not None else {}),
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def mark_task_outbox_failed(outbox_id: int | None, error: BaseException | str) -> None:
    if not outbox_id:
        return

    SessionLocal, _ = _get_session_factory()
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE task_outbox
                SET retry_count = retry_count + 1,
                    status = :pending_status,
                    error_message = :error_message,
                    next_retry_at = CASE
                        WHEN retry_count + 1 >= max_retries THEN NULL
                        ELSE CURRENT_TIMESTAMP + (
                            LEAST(
                                :max_delay_seconds,
                                :base_delay_seconds * POWER(2, retry_count)
                            ) * INTERVAL '1 second'
                        )
                    END,
                    last_attempt_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP,
                    dead_letter_at = CASE
                        WHEN retry_count + 1 >= max_retries THEN COALESCE(dead_letter_at, CURRENT_TIMESTAMP)
                        ELSE dead_letter_at
                    END,
                    completed_at = CASE
                        WHEN retry_count + 1 >= max_retries THEN COALESCE(completed_at, CURRENT_TIMESTAMP)
                        ELSE completed_at
                    END
                WHERE id = :outbox_id
                  AND status <> :done_status
                  AND retry_count < max_retries
                """
            ),
            {
                "outbox_id": outbox_id,
                "pending_status": TASK_OUTBOX_PENDING,
                "done_status": TASK_OUTBOX_DONE,
                "error_message": _safe_error_message(error),
                "base_delay_seconds": get_retry_base_delay_seconds(),
                "max_delay_seconds": get_retry_max_delay_seconds(),
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def fetch_retryable_task_outboxes(
    *,
    limit: int,
    stale_after_seconds: int,
    pending_grace_seconds: int,
) -> list[dict[str, Any]]:
    _ = stale_after_seconds
    SessionLocal, _ = _get_session_factory()
    db = SessionLocal()
    try:
        rows = db.execute(
            text(
                """
                SELECT
                    id,
                    task_type,
                    queue_name,
                    payload,
                    retry_count,
                    max_retries,
                    status,
                    rq_job_id
                FROM task_outbox
                WHERE status = :pending_status
                  AND retry_count < max_retries
                  AND created_at <= CURRENT_TIMESTAMP - (
                      :pending_grace_seconds * INTERVAL '1 second'
                  )
                  AND (next_retry_at IS NULL OR next_retry_at <= CURRENT_TIMESTAMP)
                ORDER BY created_at ASC
                LIMIT :limit
                """
            ),
            {
                "pending_status": TASK_OUTBOX_PENDING,
                "pending_grace_seconds": pending_grace_seconds,
                "limit": limit,
            },
        ).mappings()
        return [dict(row) for row in rows]
    finally:
        db.close()


def reset_task_outbox_for_retry(outbox_id: int | None) -> None:
    if not outbox_id:
        return

    SessionLocal, _ = _get_session_factory()
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE task_outbox
                SET status = :status,
                    rq_job_id = NULL,
                    retry_count = 0,
                    next_retry_at = NULL,
                    error_message = NULL,
                    dead_letter_at = NULL,
                    completed_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :outbox_id
                  AND status <> :done_status
                """
            ),
            {
                "outbox_id": outbox_id,
                "status": TASK_OUTBOX_PENDING,
                "done_status": TASK_OUTBOX_DONE,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def requeue_task_outbox(outbox_row: dict[str, Any], redis_connection: Any) -> str:
    from rq import Queue

    task_type = str(outbox_row["task_type"])
    route = OUTBOX_TASK_ROUTES.get(task_type)
    if route is None:
        raise ValueError(f"No outbox route configured for task_type={task_type!r}")

    func_name, job_timeout = route
    outbox_id = int(outbox_row["id"])
    payload = dict(outbox_row.get("payload") or {})
    payload["outbox_id"] = outbox_id

    queue = Queue(str(outbox_row["queue_name"]), connection=redis_connection)
    job = queue.enqueue(func_name, payload, job_timeout=job_timeout)
    mark_task_outbox_enqueued(outbox_id, job.id)
    return str(job.id)


def get_outbox_id(payload: dict[str, Any]) -> int | None:
    outbox_id = payload.get("outbox_id")
    if outbox_id is None:
        return None
    return int(outbox_id)


def run_with_outbox(
    payload: dict[str, Any],
    func: Callable[[], _RESULT],
) -> _RESULT:
    outbox_id = get_outbox_id(payload)
    try:
        result = func()
    except Exception as exc:
        mark_task_outbox_failed(outbox_id, exc)
        raise

    mark_task_outbox_done(outbox_id, result)
    return result
