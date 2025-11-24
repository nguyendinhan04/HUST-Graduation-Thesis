from airflow import Dataset
from airflow.decorators import dag, task
from pendulum import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from job_crawler.beautifulsoup.crawl_search_page import crawl_multiple_keywords
import pandas as pd
# from sqlite.Job2DB import hehe



with DAG(
        'crawl_search_page',
        start_date=datetime(2025,11,21),
        # schedule_interval = '0 15 * * *',
        schedule_interval = None,
        catchup=False
) as dag:
    crawl_search_page = PythonOperator(
        task_id="crawl_search_page",
        python_callable=crawl_multiple_keywords,
        # them phan op_args : op_args=[MyDataReader("/tmp/{{ ds }}/my_file")],
    )
