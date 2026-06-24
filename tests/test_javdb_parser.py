from scrapling import Selector

from spiders.javdb.javdb_constants import TASK_STATUS_PENDING, TASK_STATUS_SKIPPED
from spiders.javdb.javdb_parser import (
    has_chinese_text,
    is_fc2_task,
    parse_detail_page,
    parse_search_page,
)


def test_parse_search_page_empty():
    page = Selector("<html><body></body></html>")

    assert parse_search_page(page, source_page=1) == []


def test_parse_search_page_item():
    page = Selector(
        """
        <div class="item">
          <a class="box" href="/v/abc" title="Movie Title">
            <img src="cover.jpg">
            <div class="video-title"><strong>ABC-123</strong></div>
          </a>
        </div>
        """
    )

    assert parse_search_page(page, source_page=3, parent_task_name="VR") == [
        {
            "url": "https://javdb.com/v/abc",
            "name": "Movie Title",
            "code": "ABC-123",
            "source_page": 3,
            "parent_task_name": "VR",
            "status": TASK_STATUS_PENDING,
            "cover": "cover.jpg",
        }
    ]


def test_parse_search_page_marks_fc2_skipped():
    page = Selector(
        """
        <div class="item">
          <a class="box" href="/v/fc2-test" title="FC2-12345">
            <div class="video-title"><strong>FC2-12345</strong></div>
          </a>
        </div>
        """
    )

    tasks = parse_search_page(page, source_page=1)

    assert tasks[0]["status"] == TASK_STATUS_SKIPPED
    assert tasks[0]["reason"] == "filtered_fc2"


def test_is_fc2_task_by_name():
    assert is_fc2_task("FC2-12345", None, None) is True


def test_is_fc2_task_by_url():
    assert is_fc2_task(None, "https://example.com/fc2-12345", None) is True


def test_is_fc2_task_false():
    assert is_fc2_task("SSIS-001", "https://example.com/v/abc", "SSIS-001") is False


def test_has_chinese_text():
    assert has_chinese_text("中文字幕") is True
    assert has_chinese_text("SSIS-001") is False


def test_parse_search_page_only_chinese_filter():
    page = Selector(
        """
        <div class="item">
          <a class="box" href="/v/abc" title="ABC-001">
            <div class="video-title"><strong>ABC-001</strong></div>
          </a>
        </div>
        """
    )

    tasks = parse_search_page(
        page,
        source_page=1,
        parent_task_name="VR",
        filter_config={"only_chinese": True},
    )

    assert tasks[0]["status"] == TASK_STATUS_SKIPPED
    assert tasks[0]["reason"] == "filtered_not_chinese"


def test_parse_detail_page_fields_and_best_magnet():
    page = Selector(
        """
        <h2 class="title">ABC-123 Title</h2>
        <nav class="movie-panel-info">
          <div class="panel-block"><strong>日期:</strong><span class="value">2024-01-01</span></div>
          <div class="panel-block"><strong>時長:</strong><span class="value">120 分鐘</span></div>
          <div class="panel-block"><strong>評分:</strong><span class="value">4.62分 by 100人</span></div>
          <div class="panel-block"><strong>類別:</strong><span class="value"><a>VR</a><a>字幕</a></span></div>
          <div class="panel-block"><strong>演員:</strong><span class="value"><a>Alice</a></span></div>
        </nav>
        <div id="magnets-content">
          <div class="item">
            <button class="copy-to-clipboard" data-clipboard-text="magnet:?xt=1"></button>
            <div class="magnet-name"><span class="meta">1.2 GB</span><span class="tags"><span class="tag">字幕</span></span></div>
          </div>
          <div class="item">
            <button class="copy-to-clipboard" data-clipboard-text="magnet:?xt=2"></button>
            <div class="magnet-name"><span class="meta">3.0 GB</span></div>
          </div>
        </div>
        """
    )

    result = parse_detail_page(page)

    assert result["release_date"] == "2024-01-01"
    assert result["duration"] == 120
    assert result["rating"] == 4.62
    assert result["tags"] == ["VR", "字幕"]
    assert result["actors"] == ["Alice"]
    assert result["magnet"] == "magnet:?xt=1"
    assert result["size"] == 1228.8
