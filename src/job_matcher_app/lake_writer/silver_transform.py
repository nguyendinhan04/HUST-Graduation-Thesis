from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from job_matcher_app.lake_writer.settings import LakeWriterSettings
from job_matcher_app.lake_writer.storage import MinioObjectStorage


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


SILVER_SCHEMA = pa.schema(
    [
        pa.field("event_id", pa.string()),
        pa.field("event_type", pa.string()),
        pa.field("event_time", pa.timestamp("ms")),
        pa.field("event_date", pa.date32()),
        pa.field("user_id", pa.int64()),
        pa.field("job_id", pa.int64()),
        pa.field("application_id", pa.int64()),
        pa.field("recommendation_request_id", pa.string()),
        pa.field("recommendation_rank", pa.int32()),
        pa.field("rank_bucket", pa.string()),
        pa.field("algorithm_version", pa.string()),
        pa.field("source", pa.string()),
        pa.field("page_context", pa.string()),
        pa.field("is_recommendation_attributed", pa.bool_()),
        pa.field("raw_payload", pa.string()),
        pa.field("bronze_batch_id", pa.string()),
        pa.field("bronze_object_name", pa.string()),
        pa.field("silver_processed_at", pa.timestamp("ms")),
    ]
)


RECOMMENDATION_EVENT_TYPES = (
    "recommendation_impression",
    "recommendation_click",
    "job_application_created",
)


def _target_date(explicit_date: date | None = None) -> date:
    if explicit_date is not None:
        return explicit_date
    value = os.getenv("SILVER_PROCESS_DATE")
    if value:
        return date.fromisoformat(value)
    return datetime.utcnow().date() - timedelta(days=1)


def _rank_bucket(rank_value: Any) -> str:
    if rank_value is None:
        return "unknown"
    try:
        rank = int(rank_value)
    except (TypeError, ValueError):
        return "unknown"
    if rank == 1:
        return "1"
    if rank <= 5:
        return "2-5"
    if rank <= 10:
        return "6-10"
    if rank <= 20:
        return "11-20"
    return "20+"


def _safe_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is None else value.replace(tzinfo=None)
    if value is None:
        return datetime.utcnow()
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)


def _event_prefix(settings: LakeWriterSettings, event_type: str, metric_date: date) -> str:
    return (
        f"{settings.bronze_prefix.strip('/')}/event_type={event_type}/"
        f"year={metric_date.year:04d}/month={metric_date.month:02d}/day={metric_date.day:02d}/"
    )


def _json_load(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return {}


def _normalize_row(row: dict[str, Any], bronze_object_name: str) -> dict[str, Any] | None:
    event_type = str(row.get("event_type") or "")
    if event_type not in RECOMMENDATION_EVENT_TYPES:
        return None

    payload = _json_load(row.get("payload"))
    event_time = _safe_datetime(row.get("event_time") or payload.get("event_time"))
    recommendation_request_id = (
        str(payload.get("recommendation_request_id") or row.get("request_id") or "")
        or None
    )
    recommendation_rank = payload.get("recommendation_rank", payload.get("rank", row.get("rank")))
    application_id = payload.get("application_id")
    job_id = payload.get("job_id", row.get("entity_id"))
    user_id = payload.get("user_id", row.get("user_id"))
    algorithm_version = payload.get("algorithm_version") or "unknown"
    source = payload.get("source") or ""
    page_context = payload.get("page_context") or ""
    attributed = bool(recommendation_request_id)

    if event_type == "job_application_created" and not attributed:
        return None

    return {
        "event_id": str(row.get("event_id") or ""),
        "event_type": event_type,
        "event_time": event_time,
        "event_date": event_time.date(),
        "user_id": int(user_id) if user_id is not None else None,
        "job_id": int(job_id) if job_id is not None else None,
        "application_id": int(application_id) if application_id is not None else None,
        "recommendation_request_id": recommendation_request_id,
        "recommendation_rank": int(recommendation_rank) if recommendation_rank is not None else None,
        "rank_bucket": _rank_bucket(recommendation_rank),
        "algorithm_version": str(algorithm_version),
        "source": str(source),
        "page_context": str(page_context),
        "is_recommendation_attributed": attributed,
        "raw_payload": json.dumps(payload, ensure_ascii=False, default=str),
        "bronze_batch_id": str(row.get("batch_id") or ""),
        "bronze_object_name": bronze_object_name,
        "silver_processed_at": datetime.utcnow(),
    }


def _collect_bronze_rows(
    storage: MinioObjectStorage,
    metric_date: date,
) -> list[dict[str, Any]]:
    bronze_rows: dict[str, dict[str, Any]] = {}
    for event_type in RECOMMENDATION_EVENT_TYPES:
        prefix = _event_prefix(storage.settings, event_type, metric_date)
        for key in storage.list_parquet_keys(prefix):
            try:
                raw_bytes = storage.get_bytes(key)
                table = pq.read_table(BytesIO(raw_bytes))
                for row in table.to_pylist():
                    normalized = _normalize_row(row, key)
                    if not normalized:
                        continue
                    event_id = normalized["event_id"]
                    if event_id:
                        bronze_rows[event_id] = normalized
            except Exception as e:
                logger.error(f"WARNING: File {key} bi hong hoac rong. Bo qua file nay. Error: {e}")
                continue
    return list(bronze_rows.values())


def _write_silver_partition(
    storage: MinioObjectStorage,
    rows: list[dict[str, Any]],
    metric_date: date,
    event_type: str,
) -> str | None:
    if not rows:
        return None

    table = pa.Table.from_pylist(rows, schema=SILVER_SCHEMA)
    sink = BytesIO()
    pq.write_table(table, sink, compression="zstd")
    object_name = (
        f"{storage.settings.silver_prefix.strip('/')}/event_date={metric_date.isoformat()}/"
        f"event_type={event_type}/part-000.parquet"
    )
    storage.put_bytes(
        object_name,
        sink.getvalue(),
        content_type="application/vnd.apache.parquet",
    )
    return object_name


def build_silver_recommendation_events(
    metric_date: date | None = None,
) -> dict[str, Any]:
    settings = LakeWriterSettings()
    storage = MinioObjectStorage(settings)
    target_date = _target_date(metric_date)

    raw_rows = _collect_bronze_rows(storage, target_date)
    grouped_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        grouped_rows[str(row["event_type"])].append(row)

    written_objects: list[str] = []
    for event_type, rows in grouped_rows.items():
        object_name = _write_silver_partition(storage, rows, target_date, event_type)
        if object_name:
            written_objects.append(object_name)

    logger.info(
        "Wrote %s silver recommendation rows for %s",
        len(raw_rows),
        target_date.isoformat(),
    )
    return {
        "event_date": target_date.isoformat(),
        "rows": len(raw_rows),
        "objects": written_objects,
    }


def main() -> None:
    build_silver_recommendation_events()


if __name__ == "__main__":
    main()
