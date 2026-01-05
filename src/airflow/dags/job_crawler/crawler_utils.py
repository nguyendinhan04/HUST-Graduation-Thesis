import re
import unidecode
from job_crawler.proxypool.proxypool_scraper import ProxyPoolScraper
from job_crawler.proxypool.proxypool_validator import ProxyPoolValidator
from job_crawler.proxypool.redis_proxypool_client import RedisProxyPoolClient
from concurrent.futures import ThreadPoolExecutor
import json


def keyword_normalize(keyword: str) -> str:
    # chuyển từ chữ có dấu thành không dấu
    normalized = unidecode.unidecode(keyword)
    # chuyển thành chữ thường
    normalized = normalized.lower()
    # thay khoảng trắng bằng dấu gạch nối
    normalized = re.sub(r'\s+', '-', normalized)
    # thay ký tự đặc biệt bằng dấu gạch nối
    normalized = re.sub(r'[^a-z0-9\-]', '-', normalized)
    return normalized

def proxy_load_redis(proxy_webpage,testing_url, number_of_proxies, max_workers, redis_key, redis_config):
    proxy_scraper = ProxyPoolScraper(proxy_webpage)
    proxy_validator = ProxyPoolValidator(testing_url)
    proxy_stream = proxy_scraper.get_proxy_stream(number_of_proxies)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(
            proxy_validator.validate_proxy, proxy_stream
        )
        valid_proxies = filter(lambda x: x.is_valid is True, results)
        sorted_valid_proxies = sorted(
            valid_proxies, key=lambda x: x.health, reverse=True
        )
    print(f"Valid proxies: {sorted_valid_proxies}")
    with RedisProxyPoolClient(redis_key, redis_config) as client:
        client.override_existing_proxies(
            [
                json.dumps(record.proxy)
                for record in sorted_valid_proxies[:50]
            ]
        )

if __name__ == "__main__":
    test_keywords = [
        "Kỹ sư phần mềm",
        "Quản trị mạng",
        "Phát triển web",
        "Lập trình viên Java",
        "Chuyên viên phân tích dữ liệu",
        "Kinh doanh thiết bị/vật liệu xây dựng"
    ]
    for kw in test_keywords:
        print(f"Original: {kw} -> Normalized: {keyword_normalize(kw)}")
