from pymongo import IndexModel


def test_collection_names_match_existing_contract():
    from shared.database.collections import (
        CRAWL_CONFIG,
        CRAWL_COOKIES_CONFIG,
        CRAWL_RUNS,
        CRAWL_RUN_DETAIL_TASKS,
        CRAWL_SCHEDULES,
        CRAWL_TASKS,
        MOVIES,
        MOVIE_FILTERS,
        MOVIE_MAGNETS,
        STORAGE_CONFIG,
        STORAGE_COUNTERS,
        STORAGE_TASKS,
    )

    assert MOVIES == "movies"
    assert MOVIE_MAGNETS == "movie_magnets"
    assert MOVIE_FILTERS == "movie_filters"
    assert CRAWL_TASKS == "crawl_tasks"
    assert CRAWL_RUNS == "crawl_runs"
    assert CRAWL_RUN_DETAIL_TASKS == "crawl_run_detail_tasks"
    assert CRAWL_SCHEDULES == "crawl_schedules"
    assert CRAWL_CONFIG == "crawl_config"
    assert CRAWL_COOKIES_CONFIG == "crawl_cookies_config"
    assert STORAGE_CONFIG == "storage_config"
    assert STORAGE_TASKS == "storage_tasks"
    assert STORAGE_COUNTERS == "storage_counters"


def test_legacy_collection_module_reexports_shared_names():
    from app.db import collections as legacy
    from shared.database import collections as shared

    assert legacy.MOVIES == shared.MOVIES
    assert legacy.CRAWL_RUNS == shared.CRAWL_RUNS
    assert legacy.STORAGE_TASKS == shared.STORAGE_TASKS


def test_index_modules_export_index_models():
    from shared.database.indexes.content import MOVIE_INDEXES
    from shared.database.indexes.crawler import CRAWL_TASK_INDEXES
    from shared.database.indexes.storage import STORAGE_TASK_INDEXES

    assert all(isinstance(index, IndexModel) for index in MOVIE_INDEXES)
    assert all(isinstance(index, IndexModel) for index in CRAWL_TASK_INDEXES)
    assert all(isinstance(index, IndexModel) for index in STORAGE_TASK_INDEXES)
