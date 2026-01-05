import time
from dataclasses import dataclass
from job_crawler.beautifulsoup.beautifulsoup_utils import *
from contextlib import closing
from job_crawler.proxypool.header_list import headers_list

@dataclass(frozen=True)
class ProxyStatus:
    proxy: str
    health: float
    is_valid: bool


class ProxyPoolValidator:
    def __init__(self, url, timeout=10, checks=3, sleep_interval=0.1):
        self.timeout = timeout
        self.checks = checks
        self.sleep_interval = sleep_interval
        # self.parser = WebParser(url, rotate_header=True)
        self.url = url

    def validate_proxy(self, proxy_record):
        consecutive_checks = []
        print(f"Validating proxy: {proxy_record.proxy}")
        for _ in range(self.checks):
            # content = self.parser.get_content(
            #     timeout=self.timeout,
            #     proxies=proxy_record.proxy
            # )
            print(f"Testing proxy {proxy_record.proxy} in attempt {_+1} on url {self.url}")
            s = requests.Session()
            # content = get_soup(
            #     s,
            #     self.url,
            #     proxies=proxy_record.proxy
            # )
            content = None
            try:
                with closing(s.get(self.url, proxies=proxy_record.proxy, timeout=self.timeout, headers=random.choice(headers_list))) as response:
                    print("status code:", response.status_code)
                    if response.status_code == 200:
                        print("Proxy is valid.")
                        content = response.content
            except Exception as e:
                print(f"An error occurred: {e}")



            print(f"Received content: {content}")
            time.sleep(self.sleep_interval)
            consecutive_checks.append(int(content is not None))

        health = sum(consecutive_checks) / self.checks
        print(f"Proxy {proxy_record.proxy} health: {health}")
        proxy_status = ProxyStatus(
            proxy=proxy_record.proxy,
            health=health,
            is_valid=health > 0.66
        )
        # self.logger.info(f"Proxy status: {proxy_status}")
        return proxy_status
