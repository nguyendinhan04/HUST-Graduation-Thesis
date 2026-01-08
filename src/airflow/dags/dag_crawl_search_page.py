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

def task_crawl_search_page(execution_datetime,ti):
    # Format execution_datetime to 'YYYY-MM-DD HH:MM:SS'
    from datetime import datetime
    if execution_datetime:
        try:
            # Try parsing ISO format
            dt = datetime.fromisoformat(str(execution_datetime).replace('Z', '+00:00'))
            formatted_dt = dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            formatted_dt = str(execution_datetime)
        minio_path = crawl_multiple_keywords(current_time_str=formatted_dt)
        ti.xcom_push(key='minio_path', value=minio_path)
    else:
        print("No execution_datetime provided.")

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


def task_test_xcom(ti):
    ti.xcom_push(key='minio_path', value=["topcv/raw_job_link/mobile-developer-1_to_3-20251126203442.txt"])

def test_validate():
    from bs4 import BeautifulSoup
    import requests
    from contextlib import closing
    import random


    s = requests.Session()
    proxies = {
        "http": "http://195.158.8.123:3128",
        "http": "http://195.158.8.123:3128"
    }
    is_valid = False
    try:
        with closing(s.get("https://www.google.com/webhp", proxies=proxies, timeout=30,headers=random.choice(headers_list))) as response:
            print(response.status_code)
            if response.status_code == 200:
                is_valid = True
                print("Proxy is valid.")
        if is_valid:
            job_url = "https://www.topcv.vn/viec-lam/chuyen-gia-kiem-thu-danh-gia-an-ninh-thong-tin/1953666.html"
            with closing(s.get(job_url, proxies=proxies, timeout=30,headers=random.choice(headers_list))) as response:
                print(response.text)

    except Exception as e:
        print(f"An error occurred: {e}")

with DAG(
        'crawl_search_page',
        start_date=datetime(2025,11,21),
        schedule_interval = '*/30 * * * *',
        catchup=False
) as dag:

    crawl_search_page = PythonOperator(
        task_id="task_crawl_search_page",
        python_callable=task_crawl_search_page,
        op_kwargs={'execution_datetime': '{{ execution_date }}'},
    )
    crawl_search_page


    process_search_page = PythonOperator(
        task_id="task_process_search_page",
        python_callable=task_process_search_page,
    )
    process_search_page

    crawl_search_page >> process_search_page