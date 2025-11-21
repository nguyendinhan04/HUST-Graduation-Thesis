from airflow import Dataset
from airflow.decorators import dag, task
from pendulum import datetime
from airflow.operators.python import PythonOperator
from job_crawler.beautifulsoup.crawl_search_page import crawl_multiple_keywords
import pandas as pd
from airflow import DAG

# @dag(
#     start_date=datetime(2025, 1, 1),
#     schedule="0 10 * * *",
#     catchup=False,
#     doc_md=__doc__,
#     default_args={"owner": "Astro", "retries": 3},
#     tags=["example"],
# )
# def crawl_search_page():
#     crawl_search_page = PythonOperator(
#         task_id = "crawl_search_page",
#         python_callable = crawl_multiple_keywords,
#         # them phan op_args : op_args=[MyDataReader("/tmp/{{ ds }}/my_file")],
#    )



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
