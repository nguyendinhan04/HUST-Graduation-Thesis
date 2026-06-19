from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from pendulum import datetime as pendulum_datetime


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _logical_date(context: dict) -> date:
    data_interval_start = context.get("data_interval_start")
    if data_interval_start is not None:
        return data_interval_start.date()
    return datetime.utcnow().date() - timedelta(days=1)


def build_silver(**context) -> dict[str, object]:
    from job_matcher_app.lake_writer.silver_transform import build_silver_recommendation_events

    return build_silver_recommendation_events(_logical_date(context))


def build_gold(**context) -> dict[str, object]:
    from job_matcher_app.lake_writer.conversion_report import run_conversion_report

    return run_conversion_report(_logical_date(context))


with DAG(
    dag_id="lake_recommendation_daily",
    start_date=pendulum_datetime(2026, 1, 1, tz="Asia/Ho_Chi_Minh"),
    schedule_interval="15 1 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["lake", "silver", "gold"],
) as dag:
    silver_task = PythonOperator(
        task_id="build_silver_recommendation_events",
        python_callable=build_silver,
    )

    gold_task = PythonOperator(
        task_id="build_gold_recommendation_conversion",
        python_callable=build_gold,
    )

    silver_task >> gold_task
