from airflow import Dataset
from airflow.decorators import dag, task
from pendulum import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from job_crawler.beautifulsoup.crawl_search_page import crawl_multiple_keywords
from dedup.deduplicate_job_link import deduplicate_job_links
from job_crawler.crawler_utils import proxy_load_redis

# import job_crawler.beautifulsoup


headers_list = [
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    },
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Dnt": "1",
        "Referer": "https://www.google.com/",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
        "X-Amzn-Trace-Id": "Root=1-5ee7bae0-82260c065baf5ad7f0b3a3e3"
    },
    {
        "User-Agent": 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:55.0) Gecko/20100101 Firefox/55.0',
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.reddit.com/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
]




def task_process_search_page(ti):
    minio_path = ti.xcom_pull(task_ids='task_crawl_search_page', key='minio_path')
    deduplicate_job_links(minio_path)


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
def test_task_crawl_proxy():
    from job_crawler.proxypool.redis_proxypool_client import RedisProxyPoolClient
    redis_config = {
        "host": "redis",
        "port": 6379,
        "password": None,
        "db": 1
    }
    redis_client = RedisProxyPoolClient("proxy_pool", redis_config)
    redis_client.override_existing_proxies({"test_proxy": "hehehe"})


def test_task_load_proxy():
    from RedisClient.RedisClient import RedisQueueProducer
    from dedup.deduplicate_job_link import normalize_job_url
    import os
    redis_producer = RedisQueueProducer(
        redis_host=os.getenv("REDIS_HOST", "redis"),
        redis_port=int(os.getenv("REDIS_PORT", 6379)),
        queue_name=os.getenv("REDIS_QUEUE", "job-queue"),
        redis_password=os.getenv("REDIS_PASSWORD", None)
    )
    redis_producer.push_task(
        func='crawl_job_detail_task.test_task',
        max_retries=3,
        job_timeout=60
    )


with DAG(
        'test_proxy_redis_dag',
        start_date=datetime(2025, 11, 21),
        # schedule_interval = '*/30 * * * *',
        schedule_interval=None,
        catchup=False
) as dag:

    load_proxy = PythonOperator(
        task_id="task_load_proxy",
        python_callable=test_task_crawl_proxy,
    )
    load_proxy

    crawl_search_page = PythonOperator(
        task_id="task_crawl_search_page",
        python_callable=test_task_load_proxy,
        op_kwargs={'execution_datetime': '{{ execution_date }}'},
    )
    crawl_search_page

    load_proxy >> crawl_search_page