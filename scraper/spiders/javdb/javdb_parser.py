import re
from typing import Any

from scraper.core.utils import clean_text, parse_size
from scraper.spiders.javdb.javdb_constants import (
    FIELD_MAPPING,
    FILTER_KEYWORD_FC2,
    TASK_STATUS_PENDING,
    TASK_STATUS_SKIPPED,
)
from scraper.spiders.javdb.javdb_urls import build_detail_url


def _first_text(node, selectors: list[str]) -> str:
    for selector in selectors:
        value = node.css(selector).get()
        if value:
            return str(clean_text(value))
    return ""


def _all_text(node, selector: str) -> list[str]:
    values = node.css(selector).getall()
    return [str(clean_text(value)) for value in values if clean_text(value)]


def _parse_field_value(field_name: str, row) -> Any:
    text = _first_text(row, ["span.value::text", "span::text"])
    link_texts = _all_text(row, "span.value a::text") or _all_text(row, "a::text")

    if field_name == "日期":
        return text

    if field_name == "時長":
        match = re.search(r"\d+", text)
        return int(match.group()) if match else 0

    if field_name in ("導演", "导演", "片商", "系列"):
        return link_texts[0] if link_texts else text

    if field_name in ("評分", "评分"):
        match = re.search(r"([\d.]+)", text)
        return float(match.group(1)) if match else 0.0

    if field_name in ("類別", "类别", "演員", "演员"):
        return link_texts or ([text] if text else [])

    return text


def is_fc2_task(name: str | None, url: str | None, code: str | None = None) -> bool:
    values = [
        name or "",
        url or "",
        code or "",
    ]
    joined = " ".join(values).lower()

    return FILTER_KEYWORD_FC2 in joined


def parse_search_page(
    page,
    source_page: int,
    parent_task_name: str | None = None,
) -> list[dict]:
    tasks: list[dict] = []

    for node in page.css("div.item a.box"):
        name = _first_text(
            node,
            [
                "::attr(title)",
                ".video-title::text",
                ".video-title strong::text",
                "strong::text",
            ],
        )
        code = _first_text(node, [".video-title strong::text", "strong::text"])
        href = _first_text(node, ["::attr(href)", "a::attr(href)"])
        cover = _first_text(node, ["img::attr(src)", "img::attr(data-src)"])

        if not href:
            continue

        url = build_detail_url(href)
        task = {
            "url": url,
            "name": clean_text(name),
            "code": clean_text(code),
            "source_page": source_page,
            "parent_task_name": parent_task_name,
            "status": TASK_STATUS_PENDING,
        }

        if cover:
            task["cover"] = cover

        if is_fc2_task(task.get("name"), task.get("url"), task.get("code")):
            task["status"] = TASK_STATUS_SKIPPED
            task["reason"] = "filtered_fc2"

        tasks.append(task)

    return tasks


def parse_detail_page(page) -> dict:
    title = _first_text(page, ["h2.title::text", ".title::text", "title::text"])
    cover = _first_text(
        page,
        [
            ".video-cover img::attr(src)",
            ".movie-panel .cover img::attr(src)",
            "img.video-cover::attr(src)",
        ],
    )

    detail: dict[str, Any] = {
        "title": title,
        "cover": cover,
        "release_date": "",
        "duration": 0,
        "director": "",
        "maker": "",
        "series": "",
        "rating": 0.0,
        "tags": [],
        "actors": [],
    }

    for row in page.css("nav.movie-panel-info > div.panel-block, .movie-panel-info .panel-block"):
        label = _first_text(row, ["strong::text"]).rstrip(":").strip()
        key = FIELD_MAPPING.get(label)
        if not key:
            continue
        detail[key] = _parse_field_value(label, row)

    best_magnet = get_best_magnet(page)
    if best_magnet:
        detail.update(
            {
                "magnet": best_magnet["url"],
                "size": round(best_magnet["size"], 2),
                "has_chinese_sub": best_magnet["has_chinese_sub"],
            }
        )

    return detail


def parse_magnets(page) -> list[dict]:
    magnets: list[dict] = []

    for node in page.css("#magnets-content .item"):
        magnet_url = _first_text(
            node,
            [
                "button.copy-to-clipboard::attr(data-clipboard-text)",
                ".magnet-name a::attr(href)",
                "a::attr(href)",
            ],
        )
        if not magnet_url.startswith("magnet:?"):
            continue

        meta_text = _first_text(node, [".magnet-name .meta::text", ".meta::text"])
        tags = _all_text(node, ".magnet-name .tags .tag::text") or _all_text(node, ".tag::text")
        has_chinese_sub = any("字幕" in tag or "中字" in tag for tag in tags)

        magnets.append(
            {
                "url": magnet_url,
                "size": parse_size(meta_text),
                "tags": tags,
                "meta_text": meta_text,
                "has_chinese_sub": has_chinese_sub,
            }
        )

    return magnets


def get_best_magnet(page) -> dict | None:
    magnets = parse_magnets(page)
    if not magnets:
        return None

    return max(magnets, key=_calculate_magnet_weight)


def _calculate_magnet_weight(magnet: dict) -> float:
    weight = float(magnet.get("size") or 0.0)
    if magnet.get("has_chinese_sub"):
        weight += 10_000
    return weight
