import scrapy


class TopcvSpider(scrapy.Spider):
    name = "topcv"
    allowed_domains = ["www.topcv.vn"]
    start_urls = ["https://www.topcv.vn"]

    def parse(self, response):
        yield {
            'url': response.url,
            'body': response.text,
        }
        pass
