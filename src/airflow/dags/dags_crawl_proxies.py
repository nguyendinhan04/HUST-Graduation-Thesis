from airflow import Dataset
from airflow.decorators import dag, task
from pendulum import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from job_crawler.beautifulsoup.JobDBClient.JobDBPostgreClient import JobDBPostgreClient
from job_crawler.crawler_utils import proxy_load_redis



def task_load_proxy(ti):
    proxy_webpage = "https://free-proxy-list.net/en/ssl-proxy.html"
    testing_url = "https://www.google.com/webhp"
    number_of_proxies = 50
    max_workers = 50
    redis_key = "proxy_pool"
    redis_config = {
        "host": "redis",
        "port": 6379,
        "password": None,
        "db": 1
    }
    proxy_load_redis(
        proxy_webpage,
        testing_url,
        number_of_proxies,
        max_workers,
        redis_key,
        redis_config
    )
with DAG(
        'dag_crawl_proxies',
        start_date=datetime(2025,11,21),
        schedule_interval = '*/10 * * * *',
        catchup=False
) as dag:
    task_load_proxy_operator = PythonOperator(
        task_id='task_load_proxy',
        python_callable=task_load_proxy,
    )
    task_load_proxy_operator