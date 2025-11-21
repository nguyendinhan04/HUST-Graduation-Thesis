import sqlite3
from sqlite3 import Connection, Cursor
import os
from dotenv import load_dotenv
load_dotenv()

# doc tung file trong folder data/danh_muc_cong_viec/
data_folder = os.path.join('data', 'danh_muc_cong_viec')
db_path = os.path.join('data', 'sqlite', 'jobs.db')
conn: Connection = sqlite3.connect(db_path)
cursor: Cursor = conn.cursor()
for filename in os.listdir(data_folder):
    if filename.endswith('.txt'):
        category = filename.replace('.txt', '')
        file_path = os.path.join(data_folder, filename)
        print(category, file_path)
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                keyword = line.strip()
                if keyword:
                    cursor.execute(
                        'INSERT INTO crawl_keywords (keyword, category) VALUES (?, ?)',
                        (keyword, category)
                    )
conn.commit()