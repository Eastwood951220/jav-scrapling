from typing import Any, TypedDict


class MovieSearchItem(TypedDict, total=False):
    title: str
    code: str
    href: str
    cover: str


class MagnetItem(TypedDict, total=False):
    url: str
    size: float
    tags: list[str]
    meta_text: str
    has_chinese_sub: bool


class MovieDetailItem(TypedDict, total=False):
    title: str
    code: str
    cover: str
    magnet: str
    size: float
    has_chinese_sub: bool
    release_date: str
    duration: int
    director: str
    maker: str
    series: str
    rating: float
    tags: list[str]
    actors: list[str]


class JavdbDetailTask(TypedDict, total=False):
    url: str
    name: str
    code: str
    status: str
    source_page: int
    parent_task_name: str
    reason: str
    detail: dict[str, Any]
