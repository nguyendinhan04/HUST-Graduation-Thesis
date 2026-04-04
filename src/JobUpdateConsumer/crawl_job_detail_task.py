from datetime import datetime

from JobDetailCrawler.beautifulsoup_utils import JobDetailCrawler, smart_sleep
from JobDBClient.JobDBPostgreClient import JobDBPostgreClient
from redis import Redis
from typing import List, Optional
from proxypool.redis_proxypool_client import RedisProxyPoolClient
import os
from RedisClient.RedisClient import RedisQueueProducer

def crawl_job_detail_task(job_url: str, url_hash: str,retry_time: int) -> dict:
    """Crawl detailed job information given job URL and hash."""
    job_crawler = JobDetailCrawler()
    job_db_client = JobDBPostgreClient()

    redis_key = "proxy_pool"
    redis_config = {
        "host": "redis",
        "port": 6379,
        "password": None,
        "db": 1
    }
    redis_producer = RedisQueueProducer(
                redis_host=os.getenv("REDIS_HOST", "redis"),
                redis_port=int(os.getenv("REDIS_PORT", 6379)),
                queue_name=os.getenv("REDIS_QUEUE", "job-queue"),
                redis_password=os.getenv("REDIS_PASSWORD", None)
                )
    

    proxy = None
    redis_proxy_pool_client = RedisProxyPoolClient(redis_key,redis_config)
    with redis_proxy_pool_client as proxy_pool:
        existing_proxies = proxy_pool.list_existing_proxies()
        if existing_proxies is not None and len(existing_proxies) > 0:
            proxy = proxy_pool.get_proxy()
            job_crawler.set_proxy(proxy)
            print(f"Using proxy: {proxy} for crawling job detail.")
        else:
            if retry_time < 1:
                retry_time += 1
                print(f"No proxies available. Retrying... Attempt {retry_time} for URL: {job_url}")

                redis_producer.push_task(
                    func='crawl_job_detail_task.crawl_job_detail_task',  # Replace with actual function
                    job_url=job_url,
                    url_hash=url_hash,
                    retry_time=retry_time,
                    max_retries=3,
                    job_timeout=60
                )
                return
            else:
                print(f"Max retries reached for URL: {job_url} due to no proxies. crawl with no proxies.")
                


    try:
        job_detail = job_crawler.crawl_job_detail({"job_url": job_url, "url_hash": url_hash})
        # check if "detail_title" key  exist in job_detail
        if ("detail_title" not in job_detail or not job_detail["detail_title"]) and "brand" not in job_url:
            raise ValueError("Failed to crawl job detail or detail_title is missing.")
        current_time = datetime.now()
        job_detail.update({"datetime": current_time})
        job_db_client.insert_job_detail(job_detail)
        job_db_client.update_job_last_crawl(
                        job_detail.get("url_hash"), 
                        job_detail.get("job_url"), 
                        job_detail.get("detail_title"), 
                        current_time
                    )
        job_db_client.close()
        smart_sleep()
    except Exception as e:
        print(f"Error crawling job detail for URL: {job_url}, Error: {e}")
        if retry_time < 1:
            retry_time += 1
            print(f"Retrying... Attempt {retry_time} for URL: {job_url}")
            # return crawl_job_detail_task(job_url, url_hash, retry_time)
            redis_proxy_pool_client.lpop_proxy()
            redis_producer.push_task(
                    func='crawl_job_detail_task.crawl_job_detail_task',  # Replace with actual function
                    job_url=job_url,
                    url_hash=url_hash,
                    retry_time=retry_time,
                    max_retries=3,
                    job_timeout=60
                )
        else:
            print(f"Max retries reached for URL: {job_url}. Skipping.")


def test_task(retry_time: int = 0):

    redis_key = "proxy_pool"
    redis_config = {
        "host": "redis",
        "port": 6379,
        "password": None,
        "db": 1
    }
    proxy = None
    existing_proxies = None
    redis_proxy_pool_client = RedisProxyPoolClient(redis_key,redis_config)
    with redis_proxy_pool_client as proxy_pool:
        existing_proxies = proxy_pool.list_existing_proxies()
        if existing_proxies is not None and len(existing_proxies) > 0:
            proxy = proxy_pool.get_proxy()
            print(f"Using proxy: {proxy} for crawling job detail.")
        else:
            if retry_time < 3:
                retry_time += 1
                print(f"No proxies available. Retrying... Attempt {retry_time}")
                redis_producer = RedisQueueProducer(
                redis_host= "redis",
                redis_port=6379,
                queue_name="job-queue",
                redis_password=None
                )

                redis_producer.push_task(
                    func='crawl_job_detail_task.test_task',
                    max_retries=3,
                    retry_time=retry_time,
                    job_timeout=60
                )
                return
            else:
                print(f" crawl with no proxies.")



    print("This is a test task run after get proxy.")
    with(open(f"/app/test_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w")) as f:
        f.write(f"Proxy: {proxy} \n retry {retry_time}")