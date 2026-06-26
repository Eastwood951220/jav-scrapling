from scraper.spiders.javdb.javdb_spider import JavdbSpider


class FakeFetcher:
    def get(self, url):
        return "<html><body></body></html>"


def test_stop_check_breaks_collect_detail_tasks(monkeypatch):
    spider = JavdbSpider(FakeFetcher())
    call_count = [0]

    def stop_check():
        call_count[0] += 1
        return call_count[0] >= 2  # stop after 2 pages

    # Mock parse_search_page to return fake tasks
    monkeypatch.setattr(
        "scraper.spiders.javdb.javdb_spider.parse_search_page",
        lambda page, source_page: [
            {"code": f"ABC-{source_page:03d}", "url": "http://x.com/1", "name": "Test", "source_page": source_page, "status": "pending"}
        ]
    )
    monkeypatch.setattr(
        "scraper.spiders.javdb.javdb_spider.build_task_page_url",
        lambda url, page: f"{url}?page={page}"
    )
    monkeypatch.setattr(
        "scraper.spiders.javdb.javdb_spider.MAX_LIST_PAGES", 10
    )
    monkeypatch.setattr(
        "scraper.spiders.javdb.javdb_spider.is_security_check_page",
        lambda page: False
    )

    from scraper.tasks.task_schema import CrawlTask
    task = CrawlTask(name="test", source="javdb", url="http://x.com", url_type="javdb",
                     final_url="http://x.com", max_list_pages=10, is_skip=False)

    result = spider.collect_detail_tasks(task, stop_check=stop_check)
    # stop_check is checked before fetching each page; when it fires at page 2
    # the page hasn't been fetched yet, so only page 1 contributes
    assert len(result) == 1


def test_stop_check_breaks_run_detail_tasks():
    spider = JavdbSpider(FakeFetcher())
    call_count = [0]

    def stop_check():
        call_count[0] += 1
        return call_count[0] >= 2

    tasks = [
        {"code": "A", "url": "http://x.com/1", "name": "A", "source_page": 1, "status": "pending"},
        {"code": "B", "url": "http://x.com/2", "name": "B", "source_page": 1, "status": "pending"},
        {"code": "C", "url": "http://x.com/3", "name": "C", "source_page": 1, "status": "pending"},
    ]

    # Avoid actual network calls — the spider will try to fetch, so patch fetch
    original_fetch = spider.fetch
    spider.fetch = lambda url: "<html></html>"
    try:
        import scraper.spiders.javdb.javdb_spider as sp_mod
        original_parse = sp_mod.parse_detail_page
        sp_mod.parse_detail_page = lambda page: {"source_name": "Test"}
        original_security = sp_mod.is_security_check_page
        sp_mod.is_security_check_page = lambda page: False
        try:
            result = spider.run_detail_tasks(tasks, task_name="test", stop_check=stop_check)
            # Should stop after processing 2 items
            completed = [t for t in result if t.get("status") == "completed"]
            assert len(completed) == 1
        finally:
            sp_mod.parse_detail_page = original_parse
            sp_mod.is_security_check_page = original_security
    finally:
        spider.fetch = original_fetch
