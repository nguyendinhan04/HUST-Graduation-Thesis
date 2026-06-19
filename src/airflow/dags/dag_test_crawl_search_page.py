from airflow import Dataset
from airflow.decorators import dag, task
from pendulum import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from job_crawler.beautifulsoup.crawl_search_page import crawl_multiple_keywords,test_crawl_search_page
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




def test():
    # test_crawl_search_page()

    from curl_cffi import requests
    from bs4 import BeautifulSoup
    import json
    import re

    url = "https://www.topcv.vn/viec-lam/data-engineer/1718868.html"

    # Với curl_cffi, impersonate đã xử lý phần lớn headers chuẩn của trình duyệt. 
    # Ta chỉ cần update thêm một vài header cụ thể nếu muốn.
    headers = {
        "Referer": "https://www.topcv.vn/",
    }

    # Bật tính năng impersonate để qua mặt Cloudflare
    session = requests.Session(impersonate="chrome")
    session.headers.update(headers)
    # session.proxies.update(
    #     {'http': 'http://177.93.132.244:3128', 'https': 'http://177.93.132.244:3128'}
    # )

    # Warm-up request để lấy cookie trước khi vào trang chi tiết
    try:
        session.get("https://www.topcv.vn/", timeout=20)
    except Exception:
        pass

    try:
        resp = session.get(url, timeout=20, allow_redirects=True)
    except Exception as e:
        print(f"Request failed: {e}")
        resp = None

    html = ""
    if resp is not None:
        print(resp.content)
        if resp.status_code == 200:
            html = resp.text
        else:
            print(f"Cannot access page directly (HTTP {resp.status_code}). Continue with empty content.")

    soup = BeautifulSoup(html, "html.parser")

    job_data = {}

    # 1) Ưu tiên parse JSON-LD (thường chứa dữ liệu chuẩn của bài tuyển dụng)
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.get_text(strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                job_data["title"] = item.get("title")
                job_data["description"] = item.get("description")
                job_data["datePosted"] = item.get("datePosted")
                job_data["validThrough"] = item.get("validThrough")

                org = item.get("hiringOrganization", {})
                if isinstance(org, dict):
                    job_data["company"] = org.get("name")

                loc = item.get("jobLocation", {})
                if isinstance(loc, dict):
                    addr = loc.get("address", {})
                    if isinstance(addr, dict):
                        job_data["location"] = addr.get("addressLocality") or addr.get("addressRegion")

                salary = item.get("baseSalary")
                if salary:
                    job_data["salary"] = salary
                break

    # 2) Fallback: lấy trực tiếp từ HTML nếu thiếu
    if "title" not in job_data:
        h1 = soup.find("h1")
        if h1:
            job_data["title"] = h1.get_text(strip=True)

    if "company" not in job_data:
        company_tag = soup.select_one("a.company-name, .company-name, .job-detail__company a")
        if company_tag:
            job_data["company"] = company_tag.get_text(strip=True)

    # In kết quả
    print("=== Job Data ===")
    for k, v in job_data.items():
        print(f"{k}: {v}")


with DAG(
        'test_crawl_search_page',
        start_date=datetime(2025,11,21),
        schedule_interval = None,
        catchup=False
) as dag:

    crawl_search_page = PythonOperator(
        task_id="test_crawl_search_page",
        python_callable=test,
        op_kwargs={'execution_datetime': '{{ execution_date }}'},
    )
    crawl_search_page