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

    def close(self):
        self.cursor.close()
        self.connection.close()