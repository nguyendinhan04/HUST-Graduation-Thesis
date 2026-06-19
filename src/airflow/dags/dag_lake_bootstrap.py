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


def bootstrap_event_outbox() -> dict[str, object]:
    from job_matcher_app.event_outbox import ensure_event_outbox_table

    ensure_event_outbox_table()
    return {"bootstrapped": True}


with DAG(
    dag_id="lake_bootstrap",
    start_date=pendulum_datetime(2026, 1, 1, tz="Asia/Ho_Chi_Minh"),
    schedule_interval="@once",
    catchup=False,
    max_active_runs=1,
    tags=["lake", "bootstrap"],
) as dag:
    bootstrap_task = PythonOperator(
        task_id="bootstrap_event_outbox_schema",
        python_callable=bootstrap_event_outbox,
    )

