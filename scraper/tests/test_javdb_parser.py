from scrapling import Selector

from scraper.spiders.javdb.javdb_constants import TASK_STATUS_PENDING, TASK_STATUS_SKIPPED
from scraper.spiders.javdb.javdb_parser import (
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

    assert parse_search_page(page, source_page=3) == [
        {
            "url": "https://javdb.com/v/abc",
            "name": "Movie Title",
            "code": "ABC-123",
            "source_page": 3,
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
            <div class="magnet-name">
              <a href="magnet:?xt=urn:btih:1111111111111111111111111111111111111111">
                <span class="name">ABC-123-C.torrent</span>
                <span class="meta">1.2 GB</span>
                <span class="tags"><span class="tag">字幕</span></span>
              </a>
            </div>
            <div class="date"><span class="time">2024-01-01</span></div>
          </div>
          <div class="item">
            <div class="magnet-name">
              <a href="magnet:?xt=urn:btih:2222222222222222222222222222222222222222">
                <span class="name">ABC-123.torrent</span>
                <span class="meta">3.0 GB</span>
              </a>
            </div>
            <div class="date"><span class="time">2024-01-02</span></div>
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
    assert result["magnets"][0]["magnet"] == "magnet:?xt=urn:btih:1111111111111111111111111111111111111111"
    assert result["magnets"][0]["name"] == "ABC-123-C.torrent"
    assert result["magnets"][0]["size"] == 1228.8
    assert result["magnets"][0]["has_chinese_sub"] is True
    assert "中文字幕" in result["magnets"][0]["tags"]
