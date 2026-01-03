from urllib.parse import urljoin, urlparse, parse_qsl
from dotenv import load_dotenv
import os
from datetime import datetime
from bs4 import BeautifulSoup
from ..crawler_utils import *
from .beautifulsoup_utils import *
from .JobDBClient.JobDBPostgreClient import JobDBPostgreClient
from MinioClient.MinioClient import MinioClient
from beautifulsoup_utils import *
from ...KafkaProducer.KafkaProducer import KafkaProducerClass
from typing import List
import json

SITEMAP_URL = r"https://www.topcv.vn/sitemap.xml"


def crawl_sitemap(current_time_str: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")):
    minioClient = MinioClient()
    s = build_session()
    soup = get_soup(s, SITEMAP_URL)
    urls = []
    for url in soup.find_all("loc"):
        url_text = text(url)
        if "jobs_" in url_text:
            urls.append(
                url_text,
            )
    return urls

def crawl_sitemap_job_links(sitemap_url: str) -> List[str]:
    s = build_session()
    soup = get_soup(s, sitemap_url)
    job_db_client = JobDBPostgreClient()
    for url in soup.find_all("url"):
        
        url = url.find("loc").text
        lastmod_text = url.find("lastmod").text
        # lastmod = datetime.fromisoformat(lastmod_text)
        hash_value = url_hash(url)
        
        if job_db_client.check_job_link_exists(hash_value):
            kafka_producer = KafkaProducerClass()
            kafka_producer.send_message(
                topic="job-updates",
                message=json.dumps({
                    "url_hash": hash_value,
                    "job_url": normalize_job_url(url),
                })
            )

        

