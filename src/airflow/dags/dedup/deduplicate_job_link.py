import psycopg2
from dotenv import load_dotenv
import os
from MinioClient.MinioClient import MinioClient
from JobDBClient.JobDBPostgreClient import JobDBPostgreClient
import json



def deduplicate_job_links(links: list[str] = []):
    minioClient = MinioClient()
    dbClient = JobDBPostgreClient()
    for link in links:
        file_content = minioClient.get_text_file(bucket_name="raw" , object_name=link)
        for line in file_content.splitlines():
            record = json.loads(line.strip())
            if "url_hash" in record:
                url_hash = record["url_hash"]
                if not dbClient.check_job_link_exists(url_hash):
                    dbClient.insert_job_link(
                        url_hash=url_hash,
                        job_url=record.get("job_url"),
                        source=record.get("source"),
                        crawl_time=record.get("crawl_time")
                    )
