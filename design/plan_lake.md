# Plan: PyArrow Data Lake Writer + Recommendation Conversion Logging

  ## Summary

  Build a lightweight data lake pipeline using a Python/PyArrow worker that writes
  historical system events and recommendation tracking logs to MinIO as partitioned
  Parquet. Keep PostgreSQL/pgvector as serving storage, and use MinIO as the append-only
  historical lake for analytics, conversion-rate reporting, and future model evaluation.

  ## Data Flow

  - Backend continues normal OLTP writes to PostgreSQL.
  - Backend emits events into an event_outbox table after successful transactions.
  - A new lake-writer worker polls event_outbox, buffers events, converts them to Arrow
    tables, and writes Parquet files to MinIO.

  - Recommendation pages/API emit tracking events:
      - recommendation_impression
      - recommendation_click
      - job_apply_started
      - job_application_created

  - Conversion rate is computed from historical Parquet logs, not from request-time
    backend logic.

  Target flow:

  FastAPI
    -> PostgreSQL OLTP
    -> event_outbox
    -> PyArrow lake-writer
    -> MinIO bronze Parquet
    -> DuckDB/Airflow analytics job
    -> conversion rate report/gold Parquet

  ## Backend Events

  Add a new event_outbox table, separate from current task_outbox.

  Required fields:

  - id BIGSERIAL
  - event_id UUID UNIQUE
  - event_type VARCHAR(100)
  - entity_type VARCHAR(100)
  - entity_id BIGINT
  - user_id BIGINT NULL
  - session_id VARCHAR(255) NULL
  - request_id VARCHAR(255) NULL
  - event_time TIMESTAMP
  - schema_version INT DEFAULT 1
  - payload JSONB
  - status VARCHAR(20) DEFAULT 'pending'
  - created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  - exported_at TIMESTAMP NULL
  - error_message TEXT NULL

  Initial event types:

  - user_profile_updated
  - job_created
  - job_updated
  - recommendation_impression
  - recommendation_click
  - job_application_created

  For recommendation conversion tracking, emit:

  - recommendation_impression when recommended jobs are returned to user.
  - recommendation_click when user opens a recommended job detail.
  - job_application_created when user applies to a recommended job.

  Each recommendation event payload should include:

  - recommendation_request_id
  - algorithm_version
  - rank
  - job_id
  - score if available
  - source: tfidf, bert, rrf, or rerank
  - page_context: recommendation_home, job_detail, etc.

  ## MinIO Layout

  Use a single lake bucket, for example lake.

  Bronze paths:

  s3://lake/bronze/events/event_type=recommendation_impression/year=2026/month=06/day=11/hour=14/part-<batch_id>.parquet
  s3://lake/bronze/events/event_type=recommendation_click/year=2026/month=06/day=11/hour=14/part-<batch_id>.parquet
  s3://lake/bronze/events/event_type=job_application_created/year=2026/month=06/day=11/hour=14/part-<batch_id>.parquet

  Gold conversion report paths:

  s3://lake/gold/recommendation_conversion_daily/year=2026/month=06/day=11/part-000.parquet

  Bronze is append-only. Do not update files in place.

  ## PyArrow Lake Writer

  Create a new worker module, for example:

  src/job_matcher_app/lake_writer/
    worker.py
    minio_storage.py
    event_serializer.py
    settings.py

  Worker behavior:

  - Poll pending rows from event_outbox.
  - Lock rows with FOR UPDATE SKIP LOCKED.
  - Buffer until either:
      - LAKE_WRITER_BATCH_SIZE=1000, or
      - LAKE_WRITER_FLUSH_INTERVAL_SECONDS=30.

  - Convert events to a PyArrow table.
  - Write one Parquet file per event_type/year/month/day/hour.
  - Mark rows as exported only after MinIO write succeeds.
  - On failure, keep status pending and store error_message.

  Recommended Parquet schema:

  - event_id string
  - event_type string
  - entity_type string
  - entity_id int64
  - user_id int64
  - session_id string
  - request_id string
  - event_time timestamp[ms]
  - schema_version int32
  - payload string containing JSON
  - ingested_at timestamp[ms]
  - batch_id string

  Use pyarrow.parquet.write_table with compression:

  - compression="zstd" if available.
  - fallback compression="snappy".

  ## Conversion Rate Analytics

  Create a lightweight DuckDB or Python scheduled job to read Bronze Parquet and write
  Gold metrics.

  Daily metrics:

  - impressions
  - clicks
  - applications
  - click_through_rate = clicks / impressions
  - apply_conversion_rate = applications / impressions
  - click_to_apply_rate = applications / clicks
  - breakdown by:
      - date
      - algorithm_version
      - rank_bucket
      - job_id
      - optionally user_segment

  Rank buckets:

  - 1
  - 2-5
  - 6-10
  - 11-20
  - 20+

  Attribution rule:

  - An application counts as recommendation conversion if:
      - same user_id,
      - same job_id,
      - application occurs within 7 days after a recommendation impression or click.

  - Prefer click attribution over impression attribution if both exist.

  ## Integration Points

  - In GET /recommendations/me/jobs, generate one recommendation_request_id.
  - Include this ID in response items or store it server-side.
  - Insert one recommendation_impression event per returned job.
  - In job-detail route, accept optional recommendation_request_id and emit
    recommendation_click.

  - In apply-job route, if the user previously came from recommendation, emit
    job_application_created with attribution fields.

  Do not block API response on MinIO writes. API only writes PostgreSQL + outbox.

  ## Operational Defaults

  Environment variables:

  - LAKE_BUCKET=lake
  - LAKE_PREFIX=bronze/events
  - LAKE_WRITER_BATCH_SIZE=1000
  - LAKE_WRITER_FLUSH_INTERVAL_SECONDS=30
  - LAKE_WRITER_MAX_RETRIES=5
  - LAKE_WRITER_COMPRESSION=zstd
  - MINIO_ENDPOINT=minio:9000
  - MINIO_ACCESS_KEY=ROOTUSER
  - MINIO_SECRET_KEY=1234567890
  - MINIO_SECURE=false

  Add a Docker service:

  - lake-writer
  - uses same network as backend.

  ## Test Plan

  - Unit test event serialization from DB row to Arrow record.
  - Unit test partition path generation from event_type and event_time.
  - Integration test:
      - insert sample event_outbox rows,
      - run worker once,
      - verify Parquet files exist in MinIO,
      - verify rows are marked exported.

  - Recommendation tracking test:
      - call recommendation endpoint,
      - verify impression events are created.
      - simulate click and apply,
      - verify conversion analytics counts CTR and apply conversion correctly.

  - Failure test:
      - stop MinIO,
      - run worker,
      - verify events remain pending and can be retried.

  ## Assumptions

  - PostgreSQL/pgvector remains the online serving store.
  - MinIO lake is used for historical logs, analytics, and future offline evaluation.
  - Conversion rate is measured from recommendation impressions/clicks/applications, not
    from generic job search traffic.

  - Initial implementation can use polling from event_outbox; Kafka can be added later
    without changing the lake layout.