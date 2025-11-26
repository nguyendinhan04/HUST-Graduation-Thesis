from airflow import Dataset
from airflow.decorators import dag, task
from pendulum import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from job_crawler.beautifulsoup.JobDBClient.JobDBPostgreClient import JobDBPostgreClient



def task_setup_db_tables():
    db_client = JobDBPostgreClient()
    db_client.setup_tables()
    db_client.close()

def insert_crawl_keyword():
    db_client = JobDBPostgreClient()
    db_client.insert_crawl_keyword()
    db_client.close()

with DAG(
        'dag_setup',
        start_date=datetime(2025,11,21),
        schedule_interval = None,
        catchup=False
) as dag:
    setup_db_tables = PythonOperator(
        task_id="setup_db_tables",
        python_callable=task_setup_db_tables,
    )
    setup_db_tables


    insert_keyword = PythonOperator(
        task_id="insert_keyword",
        python_callable=insert_crawl_keyword,
    )
    insert_keyword


    setup_db_tables >> insert_keyword