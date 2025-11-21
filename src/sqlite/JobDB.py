import sqlite3
from sqlite3 import Connection, Cursor

class JobDB:
    def __init__(self, db_path: str):
        self.connection: Connection = sqlite3.connect(db_path)
        self.cursor: Cursor = self.connection.cursor()

    def execute_query(self, query: str, params: tuple = ()):
        self.cursor.execute(query, params)
        self.connection.commit()
        return self.cursor.fetchall()
    
    def get_current_crawl_keywords(self, limit: int = 10):
        self.cursor.execute('''SELECT keyword, category FROM crawl_keywords where isnull(last_crawl) LIMIT ?''', (limit,))
        crawl_keywords = self.cursor.fetchall()
        if len(crawl_keywords) < limit:
            self.cursor.execute('''SELECT keyword, category FROM crawl_keywords ORDER BY last_crawl ASC LIMIT ?''', (limit - len(crawl_keywords),))
            older_keywords = self.cursor.fetchall()
            crawl_keywords.extend(older_keywords)
        return crawl_keywords

    def close(self):
        self.connection.close()