from shared.database.collections.content import MOVIES, MOVIE_FILTERS, MOVIE_MAGNETS
from shared.database.collections.crawler import (
    CRAWL_CONFIG,
    CRAWL_COOKIES_CONFIG,
    CRAWL_RUNS,
    CRAWL_RUN_DETAIL_TASKS,
    CRAWL_SCHEDULES,
    CRAWL_TASKS,
)
from shared.database.collections.storage import (
    STORAGE_CONFIG,
    STORAGE_COUNTERS,
    STORAGE_TASKS,
)

__all__ = [
    "MOVIES",
    "MOVIE_MAGNETS",
    "MOVIE_FILTERS",
    "CRAWL_TASKS",
    "CRAWL_RUNS",
    "CRAWL_RUN_DETAIL_TASKS",
    "CRAWL_SCHEDULES",
    "CRAWL_CONFIG",
    "CRAWL_COOKIES_CONFIG",
    "STORAGE_CONFIG",
    "STORAGE_TASKS",
    "STORAGE_COUNTERS",
]
