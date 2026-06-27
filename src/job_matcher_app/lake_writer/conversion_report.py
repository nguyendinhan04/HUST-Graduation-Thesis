from __future__ import annotations

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


METRIC_SCHEMA = pa.schema(
    [
        pa.field("metric_date", pa.date32()),
        pa.field("algorithm_version", pa.string()),
        pa.field("rank_bucket", pa.string()),
        pa.field("impressions", pa.int64()),
        pa.field("clicks", pa.int64()),
        pa.field("applications", pa.int64()),
        pa.field("click_through_rate", pa.float64()),
        pa.field("apply_conversion_rate", pa.float64()),
        pa.field("click_to_apply_rate", pa.float64()),
        pa.field("computed_at", pa.timestamp("ms")),
    ]
)



def get_pg_connection():
    import psycopg2
    host = os.getenv("PG_HOST", "postgres2")
    port = os.getenv("PG_PORT", "5432")
    database = os.getenv("PG_DATABASE", "job_db_2")
    user = os.getenv("PG_USER", "airflow")
    password = os.getenv("PG_PASSWORD", "airflow")
    return psycopg2.connect(
        host=host, port=port, database=database, user=user, password=password
    )

def write_gold_metrics_to_pg(rows: list[dict[str, Any]], metric_date: date):
    if not rows:
        return
        
    import psycopg2
    from psycopg2.extras import execute_values
    
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS gold_recommendation_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_date DATE NOT NULL,
                    algorithm_version VARCHAR(255) NOT NULL,
                    rank_bucket VARCHAR(50) NOT NULL,
                    impressions INT DEFAULT 0,
                    clicks INT DEFAULT 0,
                    applications INT DEFAULT 0,
                    click_through_rate FLOAT DEFAULT 0.0,
                    apply_conversion_rate FLOAT DEFAULT 0.0,
                    click_to_apply_rate FLOAT DEFAULT 0.0,
                    computed_at TIMESTAMP NOT NULL,
                    UNIQUE(metric_date, algorithm_version, rank_bucket)
                )
            ''')
            
            cur.execute(
                "DELETE FROM gold_recommendation_metrics WHERE metric_date = %s",
                (metric_date,)
            )
            
            insert_query = '''
                INSERT INTO gold_recommendation_metrics (
                    metric_date, algorithm_version, rank_bucket,
                    impressions, clicks, applications,
                    click_through_rate, apply_conversion_rate, click_to_apply_rate,
                    computed_at
                ) VALUES %s
            '''
            
            data_to_insert = [
                (
                    row["metric_date"],
                    row["algorithm_version"],
                    row["rank_bucket"],
                    row["impressions"],
                    row["clicks"],
                    row["applications"],
                    row["click_through_rate"],
                    row["apply_conversion_rate"],
                    row["click_to_apply_rate"],
                    row["computed_at"],
                )
                for row in rows
            ]
            
            execute_values(cur, insert_query, data_to_insert)
            
        conn.commit()
        logger.info("Wrote %s rows to PostgreSQL table gold_recommendation_metrics for date %s", len(rows), metric_date)
    except Exception as e:
        conn.rollback()
        logger.error("Failed to write gold metrics to Postgres: %s", e)
    finally:
        conn.close()

def _target_date(explicit_date: date | None = None) -> date:
    if explicit_date is not None:
        return explicit_date
    value = os.getenv("CONVERSION_REPORT_DATE")
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


def _safe_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value))


def _event_prefix(settings: LakeWriterSettings, event_type: str, metric_date: date) -> str:
    return (
        f"{settings.silver_prefix.strip('/')}/event_date={metric_date.isoformat()}/"
        f"event_type={event_type}/"
    )


def _list_objects(storage: MinioObjectStorage, prefix: str) -> list[str]:
    return storage.list_parquet_keys(prefix)


def _read_silver_events(
    storage: MinioObjectStorage,
    event_type: str,
    metric_date: date,
) -> list[dict[str, Any]]:
    prefix = _event_prefix(storage.settings, event_type, metric_date)
    keys = _list_objects(storage, prefix)
    rows: list[dict[str, Any]] = []

    for key in keys:
        table = pq.read_table(BytesIO(storage.get_bytes(key)))
        rows.extend(table.to_pylist())

    logger.info("Read %s %s events from %s", len(rows), event_type, prefix)
    return rows


def _metric_key(row: dict[str, Any]) -> tuple[str, str]:
    algorithm_version = str(row.get("algorithm_version") or "unknown")
    rank_bucket = str(row.get("rank_bucket") or _rank_bucket(row.get("recommendation_rank")))
    return algorithm_version, rank_bucket


def _has_recommendation_attribution(row: dict[str, Any]) -> bool:
    return bool(row.get("recommendation_request_id"))


def build_conversion_metrics(
    *,
    impressions: list[dict[str, Any]],
    clicks: list[dict[str, Any]],
    applications: list[dict[str, Any]],
    metric_date: date,
) -> list[dict[str, Any]]:
    counters: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"impressions": 0, "clicks": 0, "applications": 0}
    )

    for row in impressions:
        if not _has_recommendation_attribution(row):
            continue
        counters[_metric_key(row)]["impressions"] += 1
    for row in clicks:
        if not _has_recommendation_attribution(row):
            continue
        counters[_metric_key(row)]["clicks"] += 1
    for row in applications:
        if not _has_recommendation_attribution(row):
            continue
        counters[_metric_key(row)]["applications"] += 1

    computed_at = datetime.utcnow()
    rows: list[dict[str, Any]] = []
    for (algorithm_version, rank_bucket), values in sorted(counters.items()):
        impressions_count = values["impressions"]
        clicks_count = values["clicks"]
        applications_count = values["applications"]
        rows.append(
            {
                "metric_date": metric_date,
                "algorithm_version": algorithm_version,
                "rank_bucket": rank_bucket,
                "impressions": impressions_count,
                "clicks": clicks_count,
                "applications": applications_count,
                "click_through_rate": (
                    clicks_count / impressions_count if impressions_count else 0.0
                ),
                "apply_conversion_rate": (
                    applications_count / impressions_count if impressions_count else 0.0
                ),
                "click_to_apply_rate": (
                    applications_count / clicks_count if clicks_count else 0.0
                ),
                "computed_at": computed_at,
            }
        )
    return rows


def write_gold_metrics(
    storage: MinioObjectStorage,
    rows: list[dict[str, Any]],
    metric_date: date,
) -> str:
    table = pa.Table.from_pylist(rows, schema=METRIC_SCHEMA)
    sink = BytesIO()
    pq.write_table(table, sink, compression="zstd")
    object_name = (
        f"{storage.settings.gold_prefix.strip('/')}/metric_date={metric_date.isoformat()}/part-000.parquet"
    )
    storage.put_bytes(
        object_name,
        sink.getvalue(),
        content_type="application/vnd.apache.parquet",
    )
    return object_name


def run_conversion_report(metric_date: date | None = None) -> dict[str, Any]:
    settings = LakeWriterSettings()
    storage = MinioObjectStorage(settings)
    target_date = _target_date(metric_date)

    impressions = _read_silver_events(
        storage,
        "recommendation_impression",
        target_date,
    )
    clicks = _read_silver_events(storage, "recommendation_click", target_date)
    applications = _read_silver_events(
        storage,
        "job_application_created",
        target_date,
    )
    rows = build_conversion_metrics(
        impressions=impressions,
        clicks=clicks,
        applications=applications,
        metric_date=target_date,
    )
    object_name = write_gold_metrics(storage, rows, target_date)
    logger.info(
        "Wrote %s recommendation conversion rows to s3://%s/%s",
        len(rows),
        settings.lake_bucket,
        object_name,
    )
    
    # Write to Postgres for BI/Grafana
    write_gold_metrics_to_pg(rows, target_date)

    return {
        "metric_date": target_date.isoformat(),
        "rows": len(rows),
        "object_name": object_name,
    }


def main() -> None:
    run_conversion_report()


if __name__ == "__main__":
    main()
