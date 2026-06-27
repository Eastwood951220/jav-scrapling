"""Tests for tags name extraction."""
from unittest.mock import MagicMock, patch


def test_extract_tags_name_listing_page():
    """Tags listing page should extract name from .section-title .section-name."""
    from scraper.spiders.javdb.javdb_parser import _extract_tags_name

    # Mock page with section-title structure (listing page)
    # No #tags div, but has .section-title .section-name
    page = MagicMock()

    # Mock _first_text behavior: node.css(selector).get()
    section_name_node = MagicMock()
    section_name_node.css.return_value.get.return_value = "VR"

    def css_side_effect(selector):
        if selector == "#tags":
            return []
        if selector == ".section-title .section-name::text":
            return section_name_node.css(selector)
        return MagicMock()

    page.css.side_effect = css_side_effect

    result = _extract_tags_name(page)
    assert result == "VR"


def test_extract_tags_name_detail_page():
    """Tags detail page should extract name from #tags div.tag.is-info."""
    from scraper.spiders.javdb.javdb_parser import _extract_tags_name

    # Mock page with #tags structure (detail page)
    page = MagicMock()

    # _first_text call for .section-title .section-name::text should return None
    first_text_result = MagicMock()
    first_text_result.get.return_value = None

    tag_elem = MagicMock()
    tag_elem.css.return_value.get.return_value = "VR"

    tags_div = MagicMock()
    tags_div.css.return_value = [tag_elem]

    def css_side_effect(selector):
        if selector == ".section-title .section-name::text":
            return first_text_result
        if selector == "#tags":
            return [tags_div]
        return MagicMock()

    page.css.side_effect = css_side_effect

    result = _extract_tags_name(page)
    assert result == "VR"


def test_extract_name_tags_not_short_circuited():
    """Tags type should NOT return empty immediately - it should fetch the page."""
    with patch("scraper.spiders.javdb.javdb_parser.parse_page_section_name", return_value="VR") as mock_parse:
        with patch("scraper.core.security.is_security_check_page", return_value=False):
            with patch("scraper.fetchers.scrapling_fetcher.ScraplingFetcher") as MockFetcher:
                mock_fetcher = MagicMock()
                MockFetcher.return_value = mock_fetcher
                mock_fetcher.get.return_value = MagicMock()

                with patch("scraper.cookies.cookie_manager.CookieManager") as MockCookie:
                    MockCookie.return_value.load.return_value = {}

                    from fastapi.testclient import TestClient
                    from app.main import app

                    client = TestClient(app)
                    response = client.post("/api/crawler/tasks/extract-name", json={
                        "url": "https://javdb.com/tags?c7=212&c10=1,2",
                        "url_type": "tags"
                    })

                    assert response.status_code == 200
                    assert response.json()["name"] == "VR"
                    mock_parse.assert_called_once()
