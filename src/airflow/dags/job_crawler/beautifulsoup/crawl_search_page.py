import redis
import hashlib
from urllib.parse import urljoin, urlparse, parse_qsl
from dotenv import load_dotenv
import os
from datetime import datetime
from bs4 import BeautifulSoup
from ..crawler_utils import *
from .beautifulsoup_utils import *
from .JobDBClient.JobDBPostgreClient import JobDBPostgreClient
from MinioClient.MinioClient import MinioClient
import json

load_dotenv()
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/sqlite/jobs.db")

# ------------ Search page ------------
def parse_search_page(soup: BeautifulSoup) -> List[Dict]:
    # soup = get_soup(session, url)
    jobs = []
    for job in soup.select("div.job-item-search-result"):
        a_title = job.select_one("h3.title a[href]")
        if not a_title:
            continue
        title = text(a_title)
        job_url = urljoin(BASE, a_title.get("href"))

        comp_a = job.select_one("a.company[href]")
        company = text(job.select_one("a.company .company-name"))
        company_url = urljoin(BASE, comp_a.get("href")) if comp_a else None

        salary = text(job.select_one("label.title-salary"))
        address = text(job.select_one("label.address .city-text"))
        exp = text(job.select_one("label.exp span"))

        jobs.append({
            "title": title,
            "job_url": (job_url),
            "company": company,
            "company_url": company_url,
            "salary_list": salary,
            "address_list": address,
            "exp_list": exp,
        })
    return jobs


def get_max_page(soup:BeautifulSoup) -> int:
    # span id="job-listing-paginate-text"
    pagination = soup.select_one("span#job-listing-paginate-text")
    if not pagination:
        return 1
    # 5 / 5 trang , 1 / 5 trang
    match = re.search(r'/\s*(\d+)\s*trang', pagination.text)
    if match:
        return int(match.group(1))
    else:
        return 1



def crawl_search_page_to_csv(query_url_template: str, start_page: int = 1, end_page: int = 1, delay_between_pages=(0.5 , 1), normalized_keyword: str = "default",current_time: datetime = datetime.now()):
    rows: List[Dict] = []
    seen_jobs = set()

    s = build_session()
    max_page = end_page
    for page in range(start_page, end_page + 1):
        url = query_url_template.format(page=page)
        print(f"[INFO] Crawling search page {page}: {url}")
        soup = get_soup(s, url)
        jobs = parse_search_page(soup)

        if not jobs:
            print(f"[INFO] Trang {page} không còn job — dừng sớm.")
            break
        max_page = get_max_page(soup=soup)

        for j in jobs:
            job_url = j["job_url"]
            job_id = urlparse(job_url).path
            if job_id in seen_jobs:
                continue
            seen_jobs.add(job_id)
            rows.append(j)
        # nghỉ giữa các trang (random)
        smart_sleep(*delay_between_pages)

        if page >= max_page:
            print(f"[INFO] Đã đạt trang cuối cùng {max_page} — dừng sớm.")
            break

    # for r in rows:
    #     r["url_hash"] = url_hash(r["job_url"]) if r["job_url"] else None

    try:
    # Lưu kết quả vào file có thể custom để lưu sang s3 hoặc database
        with open(f"data/raw/topcv/raw_job_link/{normalized_keyword}-{start_page}_to_{min(end_page, max_page)}-{current_time.strftime('%Y%m%d%H%M%S')}.txt", "a", encoding="utf-8") as f:
            for r in rows:
                f.write(f"{r}\n")
    except Exception as e:
        print(f"[ERROR] Failed to save results to file: {e}")
        raise e

    
    # with open(f"topcv_jobs_page_{start_page}_to_{end_page}.csv", "w", encoding="utf-8", newline='') as f:
    #     writer = csv.DictWriter(f, fieldnames=["title", "job_url", "company", "company_url", "salary_list", "address_list", "exp_list", "url_hash"])
    #     writer.writeheader()
    #     writer.writerows(rows)
    # conn = sqlite3.connect(SQLITE_DB_PATH)
    # cursor = conn.cursor()
    # sql_script = """
    # insert into job_links_topcv (url, hash_value, status, attempts, created_at, updated_at, source)
    # values (?, ?, 'pending', 0, datetime('now'), datetime('now'), 'topcv')
    # """
    # for r in rows:
    #     cursor.execute(sql_script, (r["job_url"], r["url_hash"]))
    # conn.commit()
    # conn.close()




def crawl_search_page_to_minio(query_url_template: str, start_page: int = 1, end_page: int = 1,ignore_end_page =  True ,delay_between_pages=(0.5 , 1), normalized_keyword: str = "default",current_time_str: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")):
    rows: List[Dict] = []
    seen_jobs = set()
    current_time = datetime.strptime(current_time_str, "%Y-%m-%d %H:%M:%S")
    s = build_session()
    max_page = end_page
    # for page in range(start_page, end_page + 1):
    #     url = query_url_template.format(page=page)
    #     print(f"[INFO] Crawling search page {page}: {url}")
    #     soup = get_soup(s, url)
    #     jobs = parse_search_page(soup)

    #     if not jobs:
    #         print(f"[INFO] Trang {page} không còn job — dừng sớm.")
    #         break
    #     max_page = get_max_page(soup=soup)

    #     for j in jobs:
    #         job_url = j["job_url"]
    #         job_id = urlparse(job_url).path
    #         if job_id in seen_jobs:
    #             continue
    #         seen_jobs.add(job_id)
    #         rows.append(j)
    #     # nghỉ giữa các trang (random)
    #     smart_sleep(*delay_between_pages)

    #     if page >= max_page:
    #         print(f"[INFO] Đã đạt trang cuối cùng {max_page} — dừng sớm.")
    #         break
    page = start_page
    while True:
        url = query_url_template.format(page=page)
        print(f"[INFO] Crawling search page {page}: {url}")
        soup = get_soup(s, url)
        jobs = parse_search_page(soup)

        if not jobs:
            print(f"[INFO] Trang {page} không còn job — dừng sớm.")
            break
        max_page = get_max_page(soup=soup)

        for j in jobs:
            job_url = normalize_job_url(j["job_url"])
            job_id = urlparse(job_url).path
            if job_id in seen_jobs:
                continue
            seen_jobs.add(job_id)
            rows.append(j)
        # nghỉ giữa các trang (random)
        smart_sleep(*delay_between_pages)

        if page > max_page:
            print(f"[INFO] Đã đạt trang cuối cùng {max_page} — dừng sớm.")
            break

        page += 1
        if not ignore_end_page and page > end_page:
            break

    

    for r in rows:
        r["url_hash"] = url_hash(r["job_url"]) if r["job_url"] else None

    try:
    # Lưu kết quả vào file có thể custom để lưu sang s3 hoặc database
        minioClient = MinioClient()
        output_data = ""
        print("the rows: " + str(len(rows)))
        for r in rows:
            output_data += json.dumps(r) + "\n"

        object_name = f"topcv/raw_job_link/{normalized_keyword}-{start_page}_to_{page-1}-{current_time.strftime('%Y%m%d%H%M%S')}.txt"
        minioClient.put_object(bucket_name="raw", object_name=object_name, input_data=output_data)
        return object_name
    except Exception as e:
        print(f"[ERROR] Failed to save results to file: {e}")
        raise e

def crawl_multiple_keywords(current_time_str: str):
    db = JobDBPostgreClient()
    crawl_keywords = db.get_current_crawl_keywords(limit=1)
    print("the kw")
    print(crawl_keywords)
    error_keywords = []
    success_keywords = []
    success_mini_path = []
    try:
        for keyword_id,keyword, category in crawl_keywords:
            print(f"[INFO] Crawling keyword: {keyword} - category: {category}")
            normalized_keyword = keyword_normalize(keyword)
            query_url_template = f"https://www.topcv.vn/tim-viec-lam-{normalized_keyword}?type_keyword=1&page={{page}}&sba=1"
            try:
                success_mini_path.append(
                    crawl_search_page_to_minio(query_url_template, start_page=1, end_page=2,
                                               normalized_keyword=normalized_keyword, current_time_str=current_time_str)
                )
                success_keywords.append(keyword_id)
            except Exception as e:
                print(f"[ERROR] Failed to crawl keyword {keyword}: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected error during crawling: {e}")
        raise e
    finally:
        error_keywords = [kw[0] for kw in crawl_keywords if kw[0] not in success_keywords]
        db.update_crawl_status(success_keywords, error_keywords, current_time_str)
        db.close()
        return success_mini_path

