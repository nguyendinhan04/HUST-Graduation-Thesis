import psycopg2
from dotenv import load_dotenv
import os
from .default_config import DEFAULTS
from MinioClient.MinioClient import MinioClient
from datetime import datetime

load_dotenv()

class JobDBPostgreClient:
    def __init__(self, host=None, port=None, database=None, user=None, password=None):
        self.connection = psycopg2.connect(
            host=host or os.getenv("PG_HOST", DEFAULTS["PG_HOST"]),
            port=port or int(os.getenv("PG_PORT", DEFAULTS["PG_PORT"])),
            database=database or os.getenv("PG_DATABASE", DEFAULTS["PG_DATABASE"]),
            user=user or os.getenv("PG_USER", DEFAULTS["PG_USER"]),
            password=password or os.getenv("PG_PASSWORD", DEFAULTS["PG_PASSWORD"])
        )
        self.cursor = self.connection.cursor()

    def execute_query(self,query: str, params: tuple = ()):
        self.cursor.execute(query, params)
        self.connection.commit()
        return self.cursor.fetchall()
    def check_job_link_exists(self, url_hash: str) -> bool:
        self.cursor.execute('''SELECT COUNT(*) FROM jobs WHERE url_hash = %s''', (url_hash,))
        count = self.cursor.fetchone()[0]
        return count > 0
    def insert_job_link(self, url_hash: str, job_url: str, name: str):
        insert_query = """
        INSERT INTO jobs (url_hash, job_url,name)
        VALUES (%s, %s, %s)
        """
        self.cursor.execute(insert_query, (
            url_hash,
            job_url,
            name,
        ))
        self.connection.commit()
    def check_company_exists(self, company_url_hash: str) -> bool:
        self.cursor.execute('''SELECT COUNT(*) FROM companies WHERE company_url_hash = %s''', (company_url_hash,))
        count = self.cursor.fetchone()[0]
        return count > 0
    def insert_company(self, name: str, company_url: str, company_url_hash: str):
        insert_query = """
        INSERT INTO companies (name, company_url, company_url_hash)
        VALUES (%s, %s, %s)
        """
        self.cursor.execute(insert_query, (
            name,
            company_url,
            company_url_hash
        ))
        self.connection.commit()

    def update_job_last_crawl(self, url_hash: str, job_url: str, name: str, datetime: datetime):
        upsert_query = """
        INSERT INTO jobs (url_hash, job_url,name, last_crawl)
        values (%s, %s, %s, %s)
        ON CONFLICT (url_hash) DO UPDATE SET last_crawl = %s
        """
        self.cursor.execute(upsert_query, (
            url_hash,
            job_url,
            name,
            datetime,
            datetime
        ))

        self.connection.commit()

    def insert_job_detail(self, job_detail: dict):
        insert_query = """
        INSERT INTO detail_jobs (url_hash, job_url, datetime, detail_title, detail_salary, detail_location, detail_experience, deadline, tags, desc_mota,desc_yeucau,desc_quyenloi,working_addresses,working_times,company_url_from_job, general_info, box_categories)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (url_hash) DO NOTHING
        """
        self.cursor.execute(insert_query, (
            job_detail.get("url_hash"),
            job_detail.get("job_url"),
            job_detail.get("datetime"),
            job_detail.get("detail_title"),
            job_detail.get("detail_salary"),
            job_detail.get("detail_location"),
            job_detail.get("detail_experience"),
            job_detail.get("deadline"),
            job_detail.get("tags"),
            job_detail.get("desc_mota"),
            job_detail.get("desc_yeucau"),
            job_detail.get("desc_quyenloi"),
            job_detail.get("working_addresses"),
            job_detail.get("working_times"),
            job_detail.get("company_url_from_job"),
            str(job_detail.get("general_info")),
            str(job_detail.get("box_categories"))
        ))
        self.connection.commit()

    def close(self):
        self.cursor.close()
        self.connection.close()