import psycopg2
from dotenv import load_dotenv
import os
from .default_config import DEFAULTS

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

    def acquire_topic_lock(self, topic_id):
        """
        Atomically acquire a lock for a topic. Returns True if lock acquired, False otherwise.
        Assumes a 'status' column in the topics table with values: 'pending', 'in_progress', 'done', 'failed'.
        """
        lock_query = """
        UPDATE topics
        SET status = 'in_progress'
        WHERE id = %s AND status = 'pending'
        RETURNING id;
        """
        self.cursor.execute(lock_query, (topic_id,))
        result = self.cursor.fetchone()
        self.connection.commit()
        return result is not None

    def release_topic_lock(self, topic_id, success=True):
        """
        Release the lock for a topic, setting status to 'done' or 'failed'.
        """
        new_status = 'done' if success else 'failed'
        release_query = """
        UPDATE topics
        SET status = %s
        WHERE id = %s;
        """
        self.cursor.execute(release_query, (new_status, topic_id))
        self.connection.commit()

    def close(self):
        self.cursor.close()
        self.connection.close()