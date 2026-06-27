from __future__ import annotations

from typing import Protocol

from scraper.config.sites import JAVDB_SITE
from scraper.cookies.cookie_manager import CookieManager
from scraper.fetchers.scrapling_fetcher import ScraplingFetcher
from scraper.spiders.javdb.javdb_spider import JavdbSpider


class ContentSourceProvider(Protocol):
    def list_items(self, query):
        raise NotImplementedError

    def get_detail(self, url: str):
        raise NotImplementedError


class JavDbProvider:
    def __init__(self, timeout: int = 30) -> None:
        self.cookie_manager = CookieManager()
        self.fetcher = ScraplingFetcher(timeout=timeout)
        self.spider = JavdbSpider(JAVDB_SITE, self.fetcher, self.cookie_manager)

    def list_items(self, query):
        return self.spider.crawl_list(query)

    def get_detail(self, url: str):
        return self.spider.crawl_detail(url)
