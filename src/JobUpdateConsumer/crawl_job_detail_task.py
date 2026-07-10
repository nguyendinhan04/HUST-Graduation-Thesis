from datetime import datetime
import time

from JobDetailCrawler.beautifulsoup_utils import JobDetailCrawler, smart_sleep
from JobDBClient.JobDBPostgreClient import JobDBPostgreClient
from redis import Redis
from typing import List, Optional
from MinioClient.MinioClient import MinioClient
import json
from proxypool.redis_proxypool_client import RedisProxyPoolClient
import os
from RedisClient.RedisClient import RedisQueueProducer

def crawl_job_detail_task(job_url: str, url_hash: str, keyword: str ,retry_time: int) -> dict:
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
    proxy = None
    redis_proxy_pool_client = RedisProxyPoolClient(redis_key,redis_config)
    with redis_proxy_pool_client as proxy_pool:
        existing_proxies = proxy_pool.list_existing_proxies()
        if existing_proxies is not None and len(existing_proxies) > 0:
            proxy = proxy_pool.get_proxy()
            job_crawler.set_proxy(proxy)
            print(f"Using proxy: {proxy} for crawling job detail.")
        else:
            if retry_time < 3:
                retry_time += 1
                print(f"No proxies available. Retrying... Attempt {retry_time} for URL: {job_url}")
                redis_producer = RedisQueueProducer(
                redis_host=os.getenv("REDIS_HOST", "redis"),
                redis_port=int(os.getenv("REDIS_PORT", 6379)),
                queue_name=os.getenv("REDIS_QUEUE", "job-queue"),
                redis_password=os.getenv("REDIS_PASSWORD", None)
                )

                redis_producer.push_task(
                    func='crawl_job_detail_task.crawl_job_detail_task',  # Replace with actual function
                    job_url=job_url,
                    url_hash=url_hash,
                    keyword=keyword,
                    retry_time=retry_time,
                    max_retries=3,
                    job_timeout=60
                )
                return
            else:
                print(f"Max retries reached for URL: {job_url} due to no proxies. crawl with no proxies.")
                


    try:
        job_detail = job_crawler.crawl_job_detail({"job_url": job_url, "url_hash": url_hash})
        current_time = datetime.now()
        job_db_client.update_job_last_crawl(
                        job_detail.get("url_hash"), 
                        job_detail.get("job_url"), 
                        job_detail.get("detail_title"),
                        keyword, 
                        current_time
                    )
        job_detail.update({"datetime": current_time.isoformat()})
        
        # Đẩy dữ liệu vào Redis List (Buffer)
        redis_client = Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD", None)
        )
        json_data = json.dumps(job_detail, ensure_ascii=False)
        redis_client.rpush("job_detail_buffer", json_data)
        
        # Self-batch logic
        BATCH_SIZE = 50
        FLUSH_INTERVAL = 600  # 10 minutes
        
        current_len = redis_client.llen("job_detail_buffer")
        last_flush = redis_client.get("job_detail_last_flush")
        if not last_flush:
            last_flush = time.time()
            redis_client.set("job_detail_last_flush", last_flush)
        
        time_since_last_flush = time.time() - float(last_flush)
        
        if current_len >= BATCH_SIZE or (current_len > 0 and time_since_last_flush >= FLUSH_INTERVAL):
            if redis_client.set("job_detail_flush_lock", "1", nx=True, ex=60):
                try:
                    current_len = redis_client.llen("job_detail_buffer")
                    items_to_pop = min(current_len, BATCH_SIZE)
                    if items_to_pop > 0:
                        batch = redis_client.lrange("job_detail_buffer", 0, items_to_pop - 1)
                        decoded_batch = [item.decode('utf-8') for item in batch]
                        data_str = "\n".join(decoded_batch)
                        
                        now = datetime.now()
                        date_path = now.strftime("year=%Y/month=%m/day=%d")
                        timestamp_str = now.strftime("%Y%m%d%H%M%S")
                        object_name = f"topcv/job_detail/{date_path}/batch_{timestamp_str}_{len(batch)}.jsonl"
                        
                        minio_client = MinioClient()
                        minio_client.put_object("bronze-layer", object_name, data_str)
                        print(f"Uploaded batch of {len(batch)} records to Minio.")
                        
                        redis_client.ltrim("job_detail_buffer", items_to_pop, -1)
                        redis_client.set("job_detail_last_flush", time.time())
                finally:
                    redis_client.delete("job_detail_flush_lock")
                    
        job_db_client.close()
        smart_sleep()
    except Exception as e:
        print(f"Error crawling job detail for URL: {job_url}, Error: {e}")
        if retry_time < 3:
            retry_time += 1
            print(f"Retrying... Attempt {retry_time} for URL: {job_url}")
            return crawl_job_detail_task(job_url, url_hash, keyword, retry_time)
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