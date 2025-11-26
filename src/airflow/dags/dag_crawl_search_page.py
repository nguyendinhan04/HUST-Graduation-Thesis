from airflow import Dataset
from airflow.decorators import dag, task
from pendulum import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from job_crawler.beautifulsoup.crawl_search_page import crawl_multiple_keywords
# import job_crawler.beautifulsoup



def task_crawl_search_page(execution_datetime):
    # Format execution_datetime to 'YYYY-MM-DD HH:MM:SS'
    from datetime import datetime
    if execution_datetime:
        try:
            # Try parsing ISO format
            dt = datetime.fromisoformat(str(execution_datetime).replace('Z', '+00:00'))
            formatted_dt = dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            formatted_dt = str(execution_datetime)
        crawl_multiple_keywords(current_time_str=formatted_dt)
    else:
        print("No execution_datetime provided.")

with DAG(
        'crawl_search_page',
        start_date=datetime(2025,11,21),
        # schedule_interval = '0 15 * * *',
        schedule_interval = None,
        catchup=False
) as dag:
    crawl_search_page = PythonOperator(
        task_id="crawl_search_page",
        python_callable=task_crawl_search_page,
        op_kwargs={'execution_datetime': '{{ execution_date }}'},
    )
