from __future__ import annotations

import logging

from airflow import DAG
from airflow.operators.python import PythonOperator
from pendulum import datetime as pendulum_datetime


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def cleanup_outbox() -> dict[str, object]:
    from job_matcher_app.lake_writer.cleanup import cleanup_exported_event_outbox

    return cleanup_exported_event_outbox()


with DAG(
    dag_id="lake_event_outbox_cleanup",
    start_date=pendulum_datetime(2026, 1, 1, tz="Asia/Ho_Chi_Minh"),
    schedule_interval="0 3 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["lake", "cleanup"],
) as dag:
    cleanup_task = PythonOperator(
        task_id="cleanup_exported_outbox",
        python_callable=cleanup_outbox,
    )
