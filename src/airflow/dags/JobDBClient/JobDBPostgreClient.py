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

    def setup_tables(self):

        create_crawl_keywords_table = f"""
        CREATE TABLE IF NOT EXISTS {os.getenv("PG_DATABASE", DEFAULTS["PG_DATABASE"])}.public.crawl_keywords (
            id SERIAL PRIMARY KEY,
            keyword VARCHAR(255) NOT NULL,
            category VARCHAR(255),
            last_crawl TIMESTAMP,
            status VARCHAR(50)
        );
        """
        create_jobs_table = f"""
        CREATE TABLE IF NOT EXISTS {os.getenv("PG_DATABASE", DEFAULTS["PG_DATABASE"])}.public.jobs (
            id SERIAL PRIMARY KEY,
            name text NOT NULL,
            job_url TEXT,
            url_hash VARCHAR(64) unique NOT NULL
        );
        """

        create_company_table = f"""
        CREATE TABLE IF NOT EXISTS {os.getenv("PG_DATABASE", DEFAULTS["PG_DATABASE"])}.public.companies (
            id SERIAL PRIMARY KEY,
            name text NOT NULL,
            company_url TEXT,
            company_url_hash VARCHAR(64) unique NOT NULL
        );
        """
        # "detail_title": title,
        # "detail_salary": salary,
        # "detail_location": location,
        # "detail_experience": experience,
        # "deadline": deadline,
        # "tags": "; ".join(tags) if tags else None,
        # "desc_mota": desc_blocks.get("Mô tả công việc"),
        # "desc_yeucau": desc_blocks.get("Yêu cầu ứng viên"),
        # "desc_quyenloi": desc_blocks.get("Quyền lợi"),
        # "working_addresses": "; ".join(addrs) if addrs else None,
        # "working_times": "; ".join(times) if times else None,
        # "company_url_from_job": company_url_detail,


        # create_job_details_table = f"""
        # CREATE TABLE IF NOT EXISTS {os.getenv("PG_DATABASE", DEFAULTS["PG_DATABASE"])}.public.job_details (
        #     id SERIAL PRIMARY KEY,
        #     job_id INT REFERENCES jobs(id),
        #     detail_title TEXT,
        #     detail_salary TEXT,
        #     detail_location TEXT,
        #     detail_experience TEXT,
        #     deadline TEXT,
        #     tags TEXT,
        #     desc_mota TEXT,
        #     desc_yeucau TEXT,
        #     desc_quyenloi TEXT,
        #     working_addresses TEXT,
        #     working_times TEXT,
        #     company_url_from_job TEXT
        # );
        # """

        
        self.cursor.execute(create_crawl_keywords_table)
        self.cursor.execute(create_jobs_table)
        self.cursor.execute(create_company_table)
        self.connection.commit()

    def insert_crawl_keyword(self):
        insert_query = """
        INSERT INTO crawl_keywords (keyword, category)
        VALUES (%s, %s)
        """
        minioClient = MinioClient()
        categories = minioClient.get_object_name_from_bucket("danh-muc-cong-viec", "")

        for category in categories:
            print(f"Processing category: {category}")
            object_content = minioClient.get_text_file("danh-muc-cong-viec", category)
            for line in object_content.splitlines():
                keyword = line.strip()
                self.cursor.execute(insert_query, (keyword, category))
        self.connection.commit()

    def execute_query(self,query: str, params: tuple = ()):
        self.cursor.execute(query, params)
        self.connection.commit()
        return self.cursor.fetchall()
    def get_current_crawl_keywords(self, limit: int = 2):
        self.cursor.execute('''SELECT id, keyword, category FROM crawl_keywords WHERE last_crawl IS NULL AND (status is null or status != 'pending') LIMIT %s''', (limit,))
        crawl_keywords = self.cursor.fetchall()
        if len(crawl_keywords) < limit:
            self.cursor.execute('''SELECT id, keyword, category FROM crawl_keywords where (status is null or status != 'pending') ORDER BY last_crawl ASC LIMIT %s''', (limit - len(crawl_keywords),))
            older_keywords = self.cursor.fetchall()
            crawl_keywords.extend(older_keywords)
        # set crawl_keywords status to pending
        try:
            print(f"[INFO] Setting crawl_keywords status to pending for keywords: {crawl_keywords}")
            placeholders = ','.join(['%s'] * len(crawl_keywords))
            self.cursor.execute(f'''UPDATE crawl_keywords SET status = 'pending' WHERE id IN ({placeholders})''', tuple([kw[0] for kw in crawl_keywords]))
            self.connection.commit()
        except Exception as e:
            print(f"[ERROR] Failed to update crawl_keywords status to pending: {e}")
            return []
        return crawl_keywords
    def update_crawl_status(self, success_keywords: list, error_keywords: list,current_time_str: str):
        for keyword_id in success_keywords:
            self.cursor.execute('''UPDATE crawl_keywords SET last_crawl = %s, status = 'success' WHERE id = %s''', (current_time_str, keyword_id))

        # de xu ly sau: log error details, retry count, etc.

        for keyword_id in error_keywords:
            self.cursor.execute('''UPDATE crawl_keywords SET last_crawl = %s, status = 'error' WHERE id = %s''', (current_time_str, keyword_id))
        self.connection.commit()


    def insert_job(self, job_data):
        insert_query = """
        INSERT INTO jobs (title, company, location, description, posted_date)
        VALUES (%s, %s, %s, %s, %s)
        """
        self.cursor.execute(insert_query, (
            job_data['title'],
            job_data['company'],
            job_data['location'],
            job_data['description'],
            job_data['posted_date']
        ))
        self.connection.commit()
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


    def close(self):
        self.cursor.close()
        self.connection.close()