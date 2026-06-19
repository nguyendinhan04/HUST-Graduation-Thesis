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


def export_bronze_events() -> dict[str, object]:
    from job_matcher_app.lake_writer.worker import LakeWriterWorker

    return {"exported": LakeWriterWorker().run_once()}


with DAG(
    dag_id="lake_bronze_export",
    start_date=pendulum_datetime(2026, 1, 1, tz="Asia/Ho_Chi_Minh"),
    schedule_interval="*/5 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["lake", "bronze"],
) as dag:
    run_export = PythonOperator(
        task_id="export_bronze_events",
        python_callable=export_bronze_events,
    )
