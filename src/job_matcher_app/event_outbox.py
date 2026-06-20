from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession


EVENT_OUTBOX_PENDING = "pending"
EVENT_OUTBOX_EXPORTING = "exporting"
EVENT_OUTBOX_EXPORTED = "exported"

_EVENT_OUTBOX_TABLE_ENSURED = False


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
    return json.dumps(value if value is not None else {}, ensure_ascii=False, default=str)


def _safe_error_message(error: BaseException | str) -> str:
    return str(error)[:4000]


def _get_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _normalize_event_id(event_id: str | uuid.UUID | None) -> str:
    return str(event_id or uuid.uuid4())


def _normalize_event_time(event_time: datetime | None) -> datetime:
    return event_time or datetime.utcnow()


def _event_outbox_ddl() -> str:
    return """
        CREATE TABLE IF NOT EXISTS event_outbox (
            id BIGSERIAL PRIMARY KEY,
            event_id UUID NOT NULL UNIQUE,
            event_type VARCHAR(100) NOT NULL,
            entity_type VARCHAR(100) NOT NULL,
            entity_id BIGINT,
            user_id BIGINT,
            session_id VARCHAR(255),
            request_id VARCHAR(255),
            event_time TIMESTAMP NOT NULL,
            schema_version INTEGER NOT NULL DEFAULT 1,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            error_message TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            exported_at TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_event_outbox_status
                CHECK (status IN ('pending', 'exporting', 'exported'))
        )
    """


def ensure_event_outbox_table() -> None:
    global _EVENT_OUTBOX_TABLE_ENSURED

    if _EVENT_OUTBOX_TABLE_ENSURED:
        return

    _, engine = _get_session_factory()
    with engine.begin() as conn:
        conn.execute(text(_event_outbox_ddl()))
        conn.execute(text("ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS error_message TEXT"))
        conn.execute(text("ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS exported_at TIMESTAMP"))
        conn.execute(text("ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"))
        conn.execute(text("ALTER TABLE event_outbox DROP CONSTRAINT IF EXISTS ck_event_outbox_status"))
        conn.execute(
            text(
                """
                ALTER TABLE event_outbox
                ADD CONSTRAINT ck_event_outbox_status
                CHECK (status IN ('pending', 'exporting', 'exported'))
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_event_outbox_status_created_at
                ON event_outbox (status, created_at)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_event_outbox_type_time
                ON event_outbox (event_type, event_time)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_event_outbox_entity
                ON event_outbox (entity_type, entity_id)
                """
            )
        )

    _EVENT_OUTBOX_TABLE_ENSURED = True


async def create_event_outbox_in_session(
    db: AsyncSession,
    *,
    event_type: str,
    entity_type: str,
    entity_id: int | None = None,
    user_id: int | None = None,
    session_id: str | None = None,
    request_id: str | None = None,
    event_time: datetime | None = None,
    schema_version: int = 1,
    payload: dict[str, Any] | None = None,
    event_id: str | uuid.UUID | None = None,
) -> int:
    outbox_id = (
        await db.execute(
            text(
                """
                INSERT INTO event_outbox (
                    event_id,
                    event_type,
                    entity_type,
                    entity_id,
                    user_id,
                    session_id,
                    request_id,
                    event_time,
                    schema_version,
                    payload,
                    status
                )
                VALUES (
                    CAST(:event_id AS uuid),
                    :event_type,
                    :entity_type,
                    :entity_id,
                    :user_id,
                    :session_id,
                    :request_id,
                    :event_time,
                    :schema_version,
                    CAST(:payload AS jsonb),
                    :status
                )
                RETURNING id
                """
            ),
            {
                "event_id": _normalize_event_id(event_id),
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "session_id": session_id,
                "request_id": request_id,
                "event_time": _normalize_event_time(event_time),
                "schema_version": schema_version,
                "payload": _json_dump(payload),
                "status": EVENT_OUTBOX_PENDING,
            },
        )
    ).scalar_one()
    return int(outbox_id)


def create_event_outbox(
    *,
    event_type: str,
    entity_type: str,
    entity_id: int | None = None,
    user_id: int | None = None,
    session_id: str | None = None,
    request_id: str | None = None,
    event_time: datetime | None = None,
    schema_version: int = 1,
    payload: dict[str, Any] | None = None,
    event_id: str | uuid.UUID | None = None,
) -> int:
    SessionLocal, _ = _get_session_factory()
    db = SessionLocal()
    try:
        outbox_id = db.execute(
            text(
                """
                INSERT INTO event_outbox (
                    event_id,
                    event_type,
                    entity_type,
                    entity_id,
                    user_id,
                    session_id,
                    request_id,
                    event_time,
                    schema_version,
                    payload,
                    status
                )
                VALUES (
                    CAST(:event_id AS uuid),
                    :event_type,
                    :entity_type,
                    :entity_id,
                    :user_id,
                    :session_id,
                    :request_id,
                    :event_time,
                    :schema_version,
                    CAST(:payload AS jsonb),
                    :status
                )
                RETURNING id
                """
            ),
            {
                "event_id": _normalize_event_id(event_id),
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "session_id": session_id,
                "request_id": request_id,
                "event_time": _normalize_event_time(event_time),
                "schema_version": schema_version,
                "payload": _json_dump(payload),
                "status": EVENT_OUTBOX_PENDING,
            },
        ).scalar_one()
        db.commit()
        return int(outbox_id)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def delete_exported_event_outboxes(retention_days: int, limit: int = 5000) -> int:
    if retention_days <= 0:
        return 0

    SessionLocal, _ = _get_session_factory()
    db = SessionLocal()
    try:
        result = db.execute(
            text(
                """
                WITH deleted AS (
                    SELECT id
                    FROM event_outbox
                    WHERE status = :status
                      AND exported_at IS NOT NULL
                      AND exported_at < CURRENT_TIMESTAMP - (:retention_days * INTERVAL '1 day')
                    ORDER BY exported_at, id
                    LIMIT :limit
                    FOR UPDATE SKIP LOCKED
                )
                DELETE FROM event_outbox eo
                USING deleted
                WHERE eo.id = deleted.id
                """
            ),
            {
                "status": EVENT_OUTBOX_EXPORTED,
                "retention_days": retention_days,
                "limit": limit,
            },
        )
        db.commit()
        return int(result.rowcount or 0)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def fetch_event_outbox_batch(limit: int) -> list[dict[str, Any]]:
    SessionLocal, _ = _get_session_factory()
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE event_outbox
                SET status = :pending_status,
                    updated_at = CURRENT_TIMESTAMP,
                    error_message = COALESCE(error_message, 'reset stale exporting event')
                WHERE status = :exporting_status
                  AND updated_at <= CURRENT_TIMESTAMP - (
                      :stale_after_seconds * INTERVAL '1 second'
                  )
                """
            ),
            {
                "pending_status": EVENT_OUTBOX_PENDING,
                "exporting_status": EVENT_OUTBOX_EXPORTING,
                "stale_after_seconds": _get_int_env(
                    "LAKE_WRITER_STALE_EXPORTING_AFTER_SECONDS",
                    900,
                ),
            },
        )
        rows = db.execute(
            text(
                """
                WITH selected AS (
                    SELECT id
                    FROM event_outbox
                    WHERE status = :pending_status
                    ORDER BY created_at ASC
                    LIMIT :limit
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE event_outbox eo
                SET status = :exporting_status,
                    error_message = NULL,
                    updated_at = CURRENT_TIMESTAMP
                FROM selected
                WHERE eo.id = selected.id
                RETURNING
                    eo.id,
                    eo.event_id::text AS event_id,
                    eo.event_type,
                    eo.entity_type,
                    eo.entity_id,
                    eo.user_id,
                    eo.session_id,
                    eo.request_id,
                    eo.event_time,
                    eo.schema_version,
                    eo.payload,
                    eo.created_at
                """
            ),
            {
                "pending_status": EVENT_OUTBOX_PENDING,
                "exporting_status": EVENT_OUTBOX_EXPORTING,
                "limit": limit,
            },
        ).mappings().all()
        db.commit()
        return [dict(row) for row in rows]
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def mark_event_outboxes_exported(outbox_ids: list[int]) -> None:
    if not outbox_ids:
        return

    SessionLocal, _ = _get_session_factory()
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE event_outbox
                SET status = :status,
                    exported_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP,
                    error_message = NULL
                WHERE id = ANY(:outbox_ids)
                """
            ),
            {"status": EVENT_OUTBOX_EXPORTED, "outbox_ids": outbox_ids},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def mark_event_outboxes_failed(outbox_ids: list[int], error: BaseException | str) -> None:
    if not outbox_ids:
        return

    SessionLocal, _ = _get_session_factory()
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE event_outbox
                SET status = :status,
                    error_message = :error_message,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ANY(:outbox_ids)
                """
            ),
            {
                "status": EVENT_OUTBOX_PENDING,
                "error_message": _safe_error_message(error),
                "outbox_ids": outbox_ids,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
