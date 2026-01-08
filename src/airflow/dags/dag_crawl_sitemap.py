from airflow import Dataset
from airflow.decorators import dag, task
from pendulum import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from job_crawler.beautifulsoup.crawl_sitemap import crawl_sitemap
from airflow.models import Variable

def task_craw_sitemap(execution_datetime):
    from datetime import datetime
    if execution_datetime:
        try:
            dt = datetime.fromisoformat(str(execution_datetime).replace('Z', '+00:00'))
            formatted_dt = dt.strftime('%Y-%m-%d %H:%M:%S')
            last_crawl_sitemap = datetime.strptime(formatted_dt, '%Y-%m-%d %H:%M:%S')
            Variable.set("last_crawl_sitemap", formatted_dt)
        except Exception:
            last_crawl_sitemap = datetime.now()
    else:
        last_crawl_sitemap = datetime.now()
    obj_execution_datetime = datetime.fromisoformat(execution_datetime)
    crawl_sitemap(obj_execution_datetime)


with DAG(
        'crawl_sitemap',
        start_date=datetime(2025,11,21),
        schedule_interval = '0 10 * * *',
        catchup=False
) as dag:
    crawl_sitemap_task = PythonOperator(
        task_id='crawl_sitemap_task',
        python_callable=task_craw_sitemap,
        op_kwargs={'execution_datetime': '{{ execution_date }}'},
    )