import os
from datetime import datetime
from .beautifulsoup_utils import *
from .JobDBClient.JobDBPostgreClient import JobDBPostgreClient
from MinioClient.MinioClient import MinioClient
from RedisClient.RedisClient import RedisQueueProducer
from job_crawler.proxypool.redis_proxypool_client import RedisProxyPoolClient
from typing import List
import json

SITEMAP_URL = r"https://www.topcv.vn/sitemap.xml"


def crawl_sitemap(last_crawl_sitemap = datetime.now()):
    minioClient = MinioClient()
    s = build_session()
    soup = get_soup(s, SITEMAP_URL)
    sitemaps_urls = []
    for url in soup.find_all("loc"):
        url_text = text(url)
        if "jobs_" in url_text:
            sitemaps_urls.append(
                url_text,
            )
    for sitemap_url in sitemaps_urls:
        print("Crawling sitemap:", sitemap_url)
        crawl_sitemap_job_links(sitemap_url,last_crawl_sitemap)

def crawl_sitemap_job_links(sitemap_url: str,last_crawl_sitemap: datetime):
    s = build_session()
    soup = get_soup(s, sitemap_url)
    job_db_client = JobDBPostgreClient()
    for url in soup.find_all("url"):
        
        job_url = url.find("loc").text
        lastmod_text = url.find("lastmod").text
        lastmod = datetime.fromisoformat(lastmod_text)
        if lastmod <= last_crawl_sitemap:
            continue
        hash_value = url_hash(job_url)
        
        if job_db_client.check_job_link_exists(hash_value):
            redis_producer = RedisQueueProducer(
                redis_host=os.getenv("REDIS_HOST", "redis"),
                redis_port=int(os.getenv("REDIS_PORT", 6379)),
                queue_name=os.getenv("REDIS_QUEUE", "job-queue"),
                redis_password=os.getenv("REDIS_PASSWORD", None)
            )

            redis_producer.push_task(
                func='crawl_job_detail_task.crawl_job_detail_task',
                job_url = normalize_job_url(job_url),
                url_hash = hash_value,
                max_retries=3,
                job_timeout=60
            )

