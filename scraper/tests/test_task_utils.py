from scraper.tasks.task_utils import build_final_url, build_page_url, determine_source


def test_build_page_url_adds_page():
    url = "https://javdb.com/actors/ZXy46?t=d&sort_type=0"

    result = build_page_url(url, 2)

    assert "page=2" in result
    assert "sort_type=0" in result
    assert "t=d" in result


def test_build_final_url_supports_lists():
    result = build_final_url(
        url="https://javdb.com/lists/y1Zrb",
        url_type="lists",
        source="javdb",
    )

    assert result == "https://javdb.com/lists/y1Zrb?page=1"


def test_build_final_url_search_relevance():
    result = build_final_url(
        url="https://javdb.com/search?q=abc",
        url_type="search",
        sort_type=0,
    )
    assert "sb=0" in result
    assert "page=1" in result


def test_build_final_url_search_date():
    result = build_final_url(
        url="https://javdb.com/search?q=abc",
        url_type="search",
        sort_type=1,
    )
    assert "sb=1" in result


def test_build_final_url_search_no_sort_param_for_actors():
    result = build_final_url(
        url="https://javdb.com/actors/ZXy46",
        url_type="actors",
        sort_type=0,
    )
    assert "sort_type=0" in result
    assert "sb=" not in result


def test_determine_source_javdb():
    assert determine_source("https://javdb.com/actors/ZXy46") == "javdb"
