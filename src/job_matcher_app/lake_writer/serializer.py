from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pyarrow as pa


EVENT_SCHEMA = pa.schema(
    [
        pa.field("outbox_id", pa.int64()),
        pa.field("event_id", pa.string()),
        pa.field("event_type", pa.string()),
        pa.field("entity_type", pa.string()),
        pa.field("entity_id", pa.int64()),
        pa.field("user_id", pa.int64()),
        pa.field("session_id", pa.string()),
        pa.field("request_id", pa.string()),
        pa.field("event_time", pa.timestamp("ms")),
        pa.field("schema_version", pa.int32()),
        pa.field("payload", pa.string()),
        pa.field("ingested_at", pa.timestamp("ms")),
        pa.field("batch_id", pa.string()),
    ]
)


def _json_dump(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, default=str)


def _naive_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def rows_to_table(rows: list[dict[str, Any]], batch_id: str) -> pa.Table:
    ingested_at = datetime.utcnow()
    records = []
    for row in rows:
        records.append(
            {
                "outbox_id": int(row["id"]),
                "event_id": str(row["event_id"]),
                "event_type": str(row["event_type"]),
                "entity_type": str(row["entity_type"]),
                "entity_id": int(row["entity_id"]) if row.get("entity_id") is not None else None,
                "user_id": int(row["user_id"]) if row.get("user_id") is not None else None,
                "session_id": row.get("session_id"),
                "request_id": row.get("request_id"),
                "event_time": _naive_datetime(row["event_time"]),
                "schema_version": int(row.get("schema_version") or 1),
                "payload": _json_dump(row.get("payload")),
                "ingested_at": ingested_at,
                "batch_id": batch_id,
            }
        )

    return pa.Table.from_pylist(records, schema=EVENT_SCHEMA)
