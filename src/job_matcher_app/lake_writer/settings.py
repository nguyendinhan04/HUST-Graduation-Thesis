from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


@dataclass(frozen=True)
class LakeWriterSettings:
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "minio:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "ROOTUSER")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "1234567890")
    minio_secure: bool = _env_bool("MINIO_SECURE", False)
    lake_bucket: str = os.getenv("LAKE_BUCKET", "lake")
    bronze_prefix: str = os.getenv("LAKE_BRONZE_PREFIX", os.getenv("LAKE_PREFIX", "bronze/events"))
    silver_prefix: str = os.getenv("LAKE_SILVER_PREFIX", "silver/recommendation_events")
    gold_prefix: str = os.getenv("LAKE_GOLD_PREFIX", "gold/recommendation_conversion_daily")
    manifest_prefix: str = os.getenv("LAKE_MANIFEST_PREFIX", "_meta/manifests")
    checkpoint_prefix: str = os.getenv("LAKE_CHECKPOINT_PREFIX", "_meta/checkpoints")
    batch_size: int = _env_int("LAKE_WRITER_BATCH_SIZE", 1000)
    flush_interval_seconds: int = _env_int("LAKE_WRITER_FLUSH_INTERVAL_SECONDS", 30)
    parquet_compression: str = os.getenv("LAKE_WRITER_COMPRESSION", "zstd")
    run_once: bool = _env_bool("LAKE_WRITER_RUN_ONCE", False)
    event_outbox_retention_days: int = _env_int("EVENT_OUTBOX_RETENTION_DAYS", 30)
    event_outbox_cleanup_batch_size: int = _env_int("EVENT_OUTBOX_CLEANUP_BATCH_SIZE", 5000)
