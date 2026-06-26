import pytest
from scraper.services.movie_service import MovieService
from scraper.tasks.task_schema import CrawlTask


class FakeFetcher:
    def get(self, url):
        return "<html></html>"


class FakeSpider:
    name = "fake"
    def run_task(self, task, on_detail_completed=None, **kwargs):
        items = [
            {"code": "ABC-001", "url": "http://x.com/1", "detail": {"source_name": "Test 1"}, "name": "Test 1", "source_page": 1, "status": "completed"},
            {"code": "ABC-002", "url": "http://x.com/2", "detail": {"source_name": "Test 2"}, "name": "Test 2", "source_page": 1, "status": "completed"},
        ]
        for item in items:
            if on_detail_completed:
                on_detail_completed(item)
        return items


def test_crawl_javdb_task_returns_items_in_result(monkeypatch):
    service = MovieService()
    monkeypatch.setattr(service, "_build_spider", lambda: FakeSpider())

    task = CrawlTask(name="test", source="javdb", url="http://x.com", final_url="http://x.com",
                     max_list_pages=1, filter=None, is_skip=False, url_type="javdb")
    result = service.crawl_javdb_task(task)

    assert "items" in result
    assert len(result["items"]) == 2
    assert result["items"][0]["code"] == "ABC-001"
    assert result["items"][0]["config_task_name"] == "test"


def test_crawl_javdb_task_does_not_import_repository():
    import scraper.services.movie_service as ms
    import inspect
    sources = inspect.getsource(ms)
    assert "MovieRepository" not in sources
    assert "repository" not in sources.lower() or "MovieRepository" not in sources
