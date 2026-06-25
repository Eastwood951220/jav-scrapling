from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from scraper.tasks.task_schema import CrawlTask


def build_crawl_task_from_doc(doc: dict[str, Any]) -> CrawlTask:
    """Build a CrawlTask from a MongoDB config_tasks document."""
    return CrawlTask(
        name=doc["name"],
        url=doc["url"],
        url_type=doc["url_type"],
        is_skip=False,
        max_list_pages=doc.get("max_list_pages", 50),
        source=doc.get("source"),
        final_url=doc.get("final_url"),
    )


def ensure_string(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def determine_source(url: str) -> str:
    url = ensure_string(url).lower()

    if "javdb.com" in url:
        return "javdb"

    return "unknown"


def append_or_replace_query(url: str, params: dict) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({key: value for key, value in params.items() if value is not None})
    new_query = urlencode(query, doseq=True)

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )


def build_final_url(
    url: str,
    url_type: str,
    source: str | None = None,
) -> str:
    url = ensure_string(url)
    url_type = ensure_string(url_type).lower()

    if not url:
        return ""

    if url_type == "search" and "?" not in url:
        return append_or_replace_query(url, {"f": "all", "page": 1})

    if source == "javdb" and url_type in ("actors", "actor"):
        return append_or_replace_query(url, {"page": 1})

    if source == "javdb" and url_type in ("lists", "list", "direct", "search"):
        return append_or_replace_query(url, {"page": 1})

    return append_or_replace_query(url, {"page": 1})


def build_page_url(final_url: str, page: int) -> str:
    return append_or_replace_query(final_url, {"page": page})
