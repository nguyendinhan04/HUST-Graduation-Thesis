from airflow import Dataset
from airflow.decorators import dag, task
from pendulum import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from job_crawler.beautifulsoup.crawl_search_page import crawl_multiple_keywords
from dedup.deduplicate_job_link import deduplicate_job_links
# import job_crawler.beautifulsoup



def task_crawl_search_page(execution_datetime,ti):
    # Format execution_datetime to 'YYYY-MM-DD HH:MM:SS'
    from datetime import datetime
    if execution_datetime:
        try:
            # Try parsing ISO format
            dt = datetime.fromisoformat(str(execution_datetime).replace('Z', '+00:00'))
            formatted_dt = dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            formatted_dt = str(execution_datetime)
        minio_path = crawl_multiple_keywords(current_time_str=formatted_dt)
        ti.xcom_push(key='minio_path', value=minio_path)
    else:
        print("No execution_datetime provided.")

def task_process_search_page(ti):
    minio_path = ti.xcom_pull(task_ids='task_crawl_search_page', key='minio_path')
    deduplicate_job_links(minio_path)


def task_test_xcom(ti):
    ti.xcom_push(key='minio_path', value=["topcv/raw_job_link/mobile-developer-1_to_3-20251126203442.txt"])

with DAG(
        'crawl_search_page',
        start_date=datetime(2025,11,21),
        # schedule_interval = '*/30 * * * *',
        schedule_interval = None,
        catchup=False
) as dag:
    crawl_search_page = PythonOperator(
        task_id="task_crawl_search_page",
        python_callable=task_crawl_search_page,
        op_kwargs={'execution_datetime': '{{ execution_date }}'},
    )
    crawl_search_page

    process_search_page = PythonOperator(
        task_id="task_process_search_page",
        python_callable=task_process_search_page,
    )
    process_search_page

    crawl_search_page >> process_search_page