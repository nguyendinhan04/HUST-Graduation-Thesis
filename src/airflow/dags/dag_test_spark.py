from airflow import Dataset
from airflow.decorators import dag, task
from pendulum import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from job_crawler.beautifulsoup.JobDBClient.JobDBPostgreClient import JobDBPostgreClient

# jars = "/opt/airflow/jars/hadoop-aws-3.3.4.jar,/opt/airflow/jars/aws-java-sdk-bundle-1.12.262.jar,/opt/airflow/jars/postgresql-42.2.18.jar,/opt/airflow/jars/delta-spark_2.12-3.3.2.jar,/opt/airflow/jars/delta-storage-3.3.2.jar,/opt/airflow/jars/delta-core_2.12-2.4.0.jar"
jars = "/opt/airflow/jars/hadoop-aws-3.3.4.jar,/opt/airflow/jars/aws-java-sdk-bundle-1.12.262.jar,/opt/airflow/jars/postgresql-42.2.18.jar,/opt/airflow/jars/delta-spark_2.12-3.3.2.jar,/opt/airflow/jars/delta-storage-3.3.2.jar"

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
        jars=jars,
        conf={
            'spark.executor.memory': '2g',
            'spark.executor.cores': '1',
            'spark.driver.memory': '1g',
        },
    )
    test_spark

