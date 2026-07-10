from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from pendulum import datetime
from datetime import timedelta

# Define the necessary JARS for S3A/MinIO and Postgres
JARS = "/opt/airflow/jars/postgresql-42.2.18.jar,/opt/airflow/jars/aws-java-sdk-bundle-1.12.262.jar,/opt/airflow/jars/hadoop-aws-3.3.4.jar"

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'lake_crawl_bronze_to_silver',
    default_args=default_args,
    start_date=datetime(2025, 11, 21, tz="Asia/Ho_Chi_Minh"),
    schedule_interval='0 1 * * *', # Chạy lúc 1:00 AM mỗi ngày
    catchup=False,
    max_active_runs=1,
    tags=['lake', 'bronze', 'silver', 'crawl_data'],
) as dag:

    # The execution_date passed to Spark job is the logical date ({{ ds }})
    # Since it runs at 1 AM today, it processes the data collected during the whole 'yesterday'.
    clean_bronze_to_silver_task = SparkSubmitOperator(
        task_id='spark_clean_bronze_to_silver',
        application='/opt/airflow/dags/spark_jobs/bronze_to_silver_cleaning.py',
        name='bronze_to_silver_cleaning_job',
        conn_id='spark_default',
        application_args=[
            '--execution_date', '{{ ds }}'
        ],
        verbose=True,
        jars=JARS,
        conf={
            'spark.executor.memory': '2g',
            'spark.executor.cores': '1',
            'spark.driver.memory': '1g',
        },
    )

    from airflow.operators.bash import BashOperator
    extract_gold_skills_task = BashOperator(
        task_id='extract_gold_skills',
        bash_command='python /opt/airflow/dags/silver_to_gold_nlp.py --execution_date {{ ds }}',
        env={
            'MINIO_ACCESS_KEY': 'ROOTUSER',
            'MINIO_SECRET_KEY': '1234567890',
            'SKILL_EXTRACTOR_MODE': 'ner_skilltrie'
        }
    )

    clean_bronze_to_silver_task >> extract_gold_skills_task
