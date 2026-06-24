from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


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
    filter_config: dict | None = None,
    source: str | None = None,
) -> str:
    url = ensure_string(url)
    url_type = ensure_string(url_type).lower()
    filter_config = filter_config or {}

    if not url:
        return ""

    if url_type == "search" and "?" not in url:
        return append_or_replace_query(url, {"f": "all", "page": 1})

    if source == "javdb" and url_type in ("actors", "actor"):
        params: dict[str, str] = {"page": 1}
        if filter_config.get("only_chinese"):
            params["t"] = "c"
        return append_or_replace_query(url, params)

    if source == "javdb" and url_type in ("lists", "list", "direct", "search"):
        return append_or_replace_query(url, {"page": 1})

    return append_or_replace_query(url, {"page": 1})


def build_page_url(final_url: str, page: int) -> str:
    return append_or_replace_query(final_url, {"page": page})
