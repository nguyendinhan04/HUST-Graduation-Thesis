import sqlite3
from sqlite3 import Connection, Cursor
from datetime import datetime

class JobDBClient:
    def __init__(self, db_path: str):
        self.connection: Connection = sqlite3.connect(db_path)
        self.cursor: Cursor = self.connection.cursor()

    def execute_query(self, query: str, params: tuple = ()):
        self.cursor.execute(query, params)
        self.connection.commit()
        return self.cursor.fetchall()
    
    def get_current_crawl_keywords(self, limit: int = 10):
        self.cursor.execute('''SELECT id, keyword, category FROM crawl_keywords WHERE last_crawl IS NULL LIMIT ?''', (limit,))
        crawl_keywords = self.cursor.fetchall()
        if len(crawl_keywords) < limit:
            self.cursor.execute('''SELECT id, keyword, category FROM crawl_keywords ORDER BY last_crawl ASC LIMIT ?''', (limit - len(crawl_keywords),))
            older_keywords = self.cursor.fetchall()
            crawl_keywords.extend(older_keywords)
        return crawl_keywords

    def update_crawl_status(self, success_keywords: list, error_keywords: list,current_time: datetime):
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        for keyword_id in success_keywords:
            self.cursor.execute('''UPDATE crawl_keywords SET last_crawl = ?, status = 'success' WHERE id = ?''', (current_time_str, keyword_id))

        # de xu ly sau: log error details, retry count, etc.

        for keyword_id in error_keywords:
            self.cursor.execute('''UPDATE crawl_keywords SET last_crawl = ?, status = 'error' WHERE id = ?''', (current_time_str, keyword_id))
        self.connection.commit()

    def close(self):
        self.connection.close()