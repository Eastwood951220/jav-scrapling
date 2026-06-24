from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from scraper.config.sites import JAVDB_SITE
from scraper.spiders.javdb.javdb_constants import DEFAULT_SEARCH_TYPE
from scraper.tasks.task_utils import build_page_url

BASE_URL = JAVDB_SITE["base_url"].rstrip("/")


def build_search_url(keyword: str, page: int = 1) -> str:
    query = urlencode(
        {
            "q": keyword,
            "f": DEFAULT_SEARCH_TYPE,
            "page": page,
        }
    )
    return f"{BASE_URL}/search?{query}"


def build_detail_url(path_or_url: str) -> str:
    if path_or_url.startswith("http"):
        return path_or_url

    if not path_or_url.startswith("/"):
        path_or_url = f"/{path_or_url}"

    return f"{BASE_URL}{path_or_url}"


def build_task_page_url(task_final_url: str, page: int) -> str:
    return build_page_url(task_final_url, page)


def merge_url_params(base_url: str, params: dict[str, list[str]], overwrite: bool = False) -> str:
    parsed = urlparse(base_url)
    existing_params = parse_qs(parsed.query)

    for key, values in params.items():
        normalized_values = values if isinstance(values, list) else [str(values)]
        if overwrite or key not in existing_params:
            existing_params[key] = normalized_values
            continue

        existing_params[key].extend(
            value for value in normalized_values if value not in existing_params[key]
        )

    query = urlencode(existing_params, doseq=True)
    return urlunparse(parsed._replace(query=query))
