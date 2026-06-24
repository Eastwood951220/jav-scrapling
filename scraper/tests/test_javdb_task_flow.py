from scrapling import Selector

from scraper.spiders.javdb.javdb_constants import (
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
    TASK_STATUS_PENDING,
    TASK_STATUS_SKIPPED,
)
from scraper.spiders.javdb.javdb_spider import JavdbSpider


class FakeFetcher:
    def __init__(self, pages):
        self.pages = list(pages)
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        page = self.pages.pop(0)

        if isinstance(page, Exception):
            raise page

        return page


def _detail_page(title="ABC-001 Title"):
    return Selector(f"<h2 class='title'>{title}</h2>")


def test_run_detail_tasks_skips_without_fetch(monkeypatch):
    monkeypatch.setattr("scraper.spiders.javdb.javdb_spider.random_sleep", lambda *args: None)

    fetcher = FakeFetcher([_detail_page()])
    spider = JavdbSpider(fetcher=fetcher)
    tasks = [
        {
            "url": "https://javdb.com/v/fc2",
            "name": "FC2-12345",
            "status": TASK_STATUS_SKIPPED,
            "reason": "filtered_fc2",
            "source_page": 1,
        },
        {
            "url": "https://javdb.com/v/abc",
            "name": "ABC-001",
            "status": TASK_STATUS_PENDING,
            "source_page": 1,
        },
    ]

    result = spider.run_detail_tasks(tasks, task_name="VR")

    assert fetcher.urls == ["https://javdb.com/v/abc"]
    assert result[0]["status"] == TASK_STATUS_SKIPPED
    assert result[1]["status"] == TASK_STATUS_COMPLETED


def test_run_detail_tasks_retries_same_task_after_security(monkeypatch):
    monkeypatch.setattr("scraper.spiders.javdb.javdb_spider.fixed_sleep", lambda *args, **kwargs: None)
    monkeypatch.setattr("scraper.spiders.javdb.javdb_spider.random_sleep", lambda *args: None)

    security_page = Selector("<html><body>Verify you are human</body></html>")
    fetcher = FakeFetcher([security_page, _detail_page()])
    spider = JavdbSpider(fetcher=fetcher)
    tasks = [
        {
            "url": "https://javdb.com/v/abc",
            "name": "ABC-001",
            "status": TASK_STATUS_PENDING,
            "source_page": 1,
        },
    ]

    result = spider.run_detail_tasks(tasks, task_name="VR")

    assert fetcher.urls == ["https://javdb.com/v/abc", "https://javdb.com/v/abc"]
    assert result[0]["status"] == TASK_STATUS_COMPLETED


def test_run_detail_tasks_failed_continues_next(monkeypatch):
    monkeypatch.setattr("scraper.spiders.javdb.javdb_spider.random_sleep", lambda *args: None)

    fetcher = FakeFetcher([RuntimeError("boom"), _detail_page("ABC-002 Title")])
    spider = JavdbSpider(fetcher=fetcher)
    tasks = [
        {
            "url": "https://javdb.com/v/abc",
            "name": "ABC-001",
            "status": TASK_STATUS_PENDING,
            "source_page": 1,
        },
        {
            "url": "https://javdb.com/v/def",
            "name": "ABC-002",
            "status": TASK_STATUS_PENDING,
            "source_page": 1,
        },
    ]

    result = spider.run_detail_tasks(tasks, task_name="VR")

    assert result[0]["status"] == TASK_STATUS_FAILED
    assert result[0]["reason"] == "boom"
    assert result[1]["status"] == TASK_STATUS_COMPLETED


def test_run_detail_tasks_calls_completion_callback(monkeypatch):
    monkeypatch.setattr("scraper.spiders.javdb.javdb_spider.random_sleep", lambda *args: None)

    fetcher = FakeFetcher([_detail_page()])
    spider = JavdbSpider(fetcher=fetcher)
    completed = []
    tasks = [
        {
            "url": "https://javdb.com/v/abc",
            "name": "ABC-001",
            "code": "ABC-001",
            "status": TASK_STATUS_PENDING,
            "source_page": 1,
        },
    ]

    spider.run_detail_tasks(
        tasks,
        task_name="VR",
        on_detail_completed=completed.append,
    )

    assert completed == [tasks[0]]
    assert completed[0]["status"] == TASK_STATUS_COMPLETED
    assert completed[0]["detail"]["title"] == "ABC-001 Title"
