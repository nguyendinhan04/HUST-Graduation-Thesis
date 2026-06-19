from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime
from io import BytesIO

import pyarrow.parquet as pq

from job_matcher_app.event_outbox import (
    ensure_event_outbox_table,
    fetch_event_outbox_batch,
    mark_event_outboxes_exported,
    mark_event_outboxes_failed,
)
from job_matcher_app.lake_writer.serializer import rows_to_table
from job_matcher_app.lake_writer.settings import LakeWriterSettings
from job_matcher_app.lake_writer.storage import MinioObjectStorage


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _partition_key(row: dict) -> tuple[str, int, int, int, int]:
    event_time = row["event_time"]
    if not isinstance(event_time, datetime):
        event_time = datetime.fromisoformat(str(event_time).replace("Z", "+00:00"))
    return (
        str(row["event_type"]),
        event_time.year,
        event_time.month,
        event_time.day,
        event_time.hour,
    )


def _object_name(
    settings: LakeWriterSettings,
    *,
    event_type: str,
    year: int,
    month: int,
    day: int,
    hour: int,
    batch_id: str,
) -> str:
    prefix = settings.bronze_prefix.strip("/")
    return (
        f"{prefix}/event_type={event_type}/year={year:04d}/month={month:02d}/"
        f"day={day:02d}/hour={hour:02d}/part-{batch_id}.parquet"
    )


def _table_to_parquet_bytes(table, compression: str) -> bytes:
    sink = BytesIO()
    try:
        pq.write_table(table, sink, compression=compression)
    except Exception:
        if compression == "snappy":
            raise
        logger.warning(
            "Parquet compression %s failed, falling back to snappy.",
            compression,
            exc_info=True,
        )
        sink = BytesIO()
        pq.write_table(table, sink, compression="snappy")
    return sink.getvalue()


class LakeWriterWorker:
    def __init__(
        self,
        settings: LakeWriterSettings | None = None,
        *,
        ensure_schema: bool = False,
    ):
        self.settings = settings or LakeWriterSettings()
        self.storage = MinioObjectStorage(self.settings)
        if ensure_schema:
            ensure_event_outbox_table()

    def run_once(self) -> int:
        rows = fetch_event_outbox_batch(self.settings.batch_size)
        if not rows:
            return 0

        written_ids: list[int] = []
        grouped_rows: dict[tuple[str, int, int, int, int], list[dict]] = defaultdict(list)
        for row in rows:
            grouped_rows[_partition_key(row)].append(row)

        try:
            for (event_type, year, month, day, hour), partition_rows in grouped_rows.items():
                batch_id = uuid.uuid4().hex
                table = rows_to_table(partition_rows, batch_id=batch_id)
                parquet_bytes = _table_to_parquet_bytes(
                    table,
                    compression=self.settings.parquet_compression,
                )
                object_name = _object_name(
                    self.settings,
                    event_type=event_type,
                    year=year,
                    month=month,
                    day=day,
                    hour=hour,
                    batch_id=batch_id,
                )
                self.storage.put_bytes(
                    object_name,
                    parquet_bytes,
                    content_type="application/vnd.apache.parquet",
                )
                partition_ids = [int(row["id"]) for row in partition_rows]
                mark_event_outboxes_exported(partition_ids)
                written_ids.extend(partition_ids)
                logger.info(
                    "Wrote %s events to s3://%s/%s",
                    len(partition_rows),
                    self.settings.lake_bucket,
                    object_name,
                )
        except Exception as exc:
            remaining_ids = [int(row["id"]) for row in rows if int(row["id"]) not in written_ids]
            mark_event_outboxes_failed(remaining_ids, exc)
            raise

        return len(rows)

    def run_forever(self) -> None:
        logger.info(
            "Starting lake writer: bucket=%s prefix=%s batch_size=%s interval=%ss",
            self.settings.lake_bucket,
            self.settings.bronze_prefix,
            self.settings.batch_size,
            self.settings.flush_interval_seconds,
        )
        self.storage.ensure_bucket()
        while True:
            exported_count = self.run_once()
            if self.settings.run_once:
                return
            if exported_count == 0:
                time.sleep(self.settings.flush_interval_seconds)


if __name__ == "__main__":
    LakeWriterWorker(ensure_schema=True).run_forever()
