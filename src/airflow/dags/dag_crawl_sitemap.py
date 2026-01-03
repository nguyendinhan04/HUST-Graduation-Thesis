from airflow import Dataset
from airflow.decorators import dag, task
from pendulum import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from job_crawler.beautifulsoup.crawl_sitemap import crawl_sitemap
from dedup.deduplicate_job_link import deduplicate_job_links
from airflow.models import Variable

def task_craw_sitemap():
    urls = crawl_sitemap()
    print(urls)


with DAG(
        'crawl_sitemap',
        start_date=datetime(2025,11,21),
        # schedule_interval = '*/30 * * * *',
        schedule_interval = None,
        catchup=False
) as dag:
    crawl_sitemap_task = PythonOperator(
        task_id='crawl_sitemap_task',
        python_callable=task_craw_sitemap
    )