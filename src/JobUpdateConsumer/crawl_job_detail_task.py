from datetime import datetime

from JobDetailCrawler.beautifulsoup_utils import JobDetailCrawler, smart_sleep
from JobDBClient.JobDBPostgreClient import JobDBPostgreClient

def crawl_job_detail_task(job_url: str, url_hash: str) -> dict:
    """Crawl detailed job information given job URL and hash."""
    job_crawler = JobDetailCrawler()
    job_db_client = JobDBPostgreClient()




    job_detail = job_crawler.crawl_job_detail({"job_url": job_url, "url_hash": url_hash})
    current_time = datetime.now()
    job_db_client.update_job_last_crawl(
                    job_detail.get("url_hash"), 
                    job_detail.get("job_url"), 
                    job_detail.get("detail_title"), 
                    current_time
                )
    job_detail.update({"datetime": current_time})
    job_db_client.insert_job_detail(job_detail)
    job_db_client.close()
    smart_sleep()