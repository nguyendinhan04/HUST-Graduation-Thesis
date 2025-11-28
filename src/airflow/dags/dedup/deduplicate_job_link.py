import hashlib
import psycopg2
from dotenv import load_dotenv
import os
from MinioClient.MinioClient import MinioClient
from JobDBClient.JobDBPostgreClient import JobDBPostgreClient
import json

def normalize_job_url(url: str) -> str:
    if not url:
        return url
    parsed_url = url.split('?')[0].split('/')[-2:]
    norm_url = '/'.join(parsed_url)
    return norm_url


def url_hash(url: str) -> str:
    norm_url = normalize_job_url(url)
    hash_object = hashlib.sha256(norm_url.encode('utf-8'))
    return hash_object.hexdigest()

def normalize_company_url(url: str) -> str:
    if not url:
        return url
    parsed_url = url.split('?')[0].rstrip('/')
    return parsed_url
def company_url_hash(url: str) -> str:
    norm_url = normalize_company_url(url)
    hash_object = hashlib.sha256(norm_url.encode('utf-8'))
    return hash_object.hexdigest()


def deduplicate_job_links(links: list[str] = []):
    minioClient = MinioClient()
    dbClient = JobDBPostgreClient()
    for link in links:
        file_content = minioClient.get_text_file(bucket_name="raw" , object_name=link)
        for line in file_content.splitlines():
            record = json.loads(line.strip())
            if "company_url" in record:
                company_url = record["company_url"]
                hash_company_url = company_url_hash(company_url) if company_url else None
                if not dbClient.check_company_exists(hash_company_url):
                    dbClient.insert_company(
                        name=record.get("company"),
                        company_url=company_url,
                        company_url_hash=hash_company_url
                    )
                else:
                    print(f"Company already exists: {company_url}")
            if "url_hash" in record:
                job_url = record["job_url"]
                url_hash_value = url_hash(job_url) if job_url else None
                if not dbClient.check_job_link_exists(url_hash_value):
                    dbClient.insert_job_link(
                        url_hash=url_hash_value,
                        job_url=record.get("job_url"),
                        name=record.get("title")

                    )
                else:
                    print(f"Job link already exists: {job_url}")
