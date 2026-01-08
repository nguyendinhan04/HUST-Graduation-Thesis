from airflow import Dataset
from airflow.decorators import dag, task
from pendulum import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from job_crawler.beautifulsoup.JobDBClient.JobDBPostgreClient import JobDBPostgreClient




with DAG(
        'test_spark',
        start_date=datetime(2025,11,21),
        schedule_interval = None,
        catchup=False
) as dag:
    test_spark = SparkSubmitOperator(
        task_id='test_spark_submit',
        application='/opt/airflow/dags/spark_jobs/test_job.py',
        name='test_spark_job',
        conn_id='spark_default',
        application_args=[],
        verbose=True,
        jars='/opt/airflow/jars/postgresql-42.2.18.jar',
        conf={
            'spark.executor.memory': '2g',
            'spark.executor.cores': '1',
            'spark.driver.memory': '1g',
        },
    )
    test_spark

