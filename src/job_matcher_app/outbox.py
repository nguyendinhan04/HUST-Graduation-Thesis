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
TASK_OUTBOX_FAILED = "failed"

_RESULT = TypeVar("_RESULT")


def _get_database_url() -> str:
    user = os.getenv("PG_USER", "airflow")
    password = os.getenv("PG_PASSWORD", "airflow")
    host = os.getenv("PG_HOST", "postgres")
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
                        CHECK (status IN ('pending', 'done', 'failed')),
                    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                    result JSONB,
                    error_message TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
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


def create_task_outbox(
    *,
    task_type: str,
    aggregate_type: str,
    aggregate_id: int,
    queue_name: str,
    payload: dict[str, Any],
) -> int:
    ensure_task_outbox_table()
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
                    payload
                )
                VALUES (
                    :task_type,
                    :aggregate_type,
                    :aggregate_id,
                    :queue_name,
                    :status,
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
    # ensure_task_outbox_table()
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
                    payload
                )
                VALUES (
                    :task_type,
                    :aggregate_type,
                    :aggregate_id,
                    :queue_name,
                    :status,
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
                "payload": _json_dump(payload),
            },
        )
    ).scalar_one()
    return int(outbox_id)


def mark_task_outbox_enqueued(outbox_id: int | None, rq_job_id: str) -> None:
    if not outbox_id:
        return

    ensure_task_outbox_table()
    SessionLocal, _ = _get_session_factory()
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE task_outbox
                SET rq_job_id = :rq_job_id,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :outbox_id
                """
            ),
            {"outbox_id": outbox_id, "rq_job_id": rq_job_id},
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

    ensure_task_outbox_table()
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

    ensure_task_outbox_table()
    SessionLocal, _ = _get_session_factory()
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE task_outbox
                SET status = :status,
                    error_message = :error_message,
                    updated_at = CURRENT_TIMESTAMP,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = :outbox_id
                """
            ),
            {
                "outbox_id": outbox_id,
                "status": TASK_OUTBOX_FAILED,
                "error_message": _safe_error_message(error),
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


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
