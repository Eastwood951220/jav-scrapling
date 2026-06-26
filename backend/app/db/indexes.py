from pymongo import ASCENDING, DESCENDING, IndexModel

from app.db.collections import (
    RUNS,
    RUN_DETAIL_TASKS,
    STORAGE_COUNTERS,
    STORAGE_TASKS,
    TASKS,
)
from scraper.database.indexes import ensure_indexes as ensure_movie_indexes


def ensure_backend_indexes(db) -> None:
    """Create indexes for fresh backend-owned collections."""
    ensure_movie_indexes(db, "movies")

    db[TASKS].create_indexes([
        IndexModel([("created_at", DESCENDING)], name="idx_crawl_tasks_created_at"),
        IndexModel([("name", ASCENDING)], name="idx_crawl_tasks_name"),
    ])

    db[RUNS].create_indexes([
        IndexModel([("task_id", ASCENDING), ("status", ASCENDING)], name="idx_crawl_runs_task_status"),
        IndexModel([("queued_at", DESCENDING)], name="idx_crawl_runs_queued_at"),
    ])

    db[RUN_DETAIL_TASKS].create_indexes([
        IndexModel([("run_id", ASCENDING), ("status", ASCENDING)], name="idx_crawl_detail_run_status"),
        IndexModel([("run_id", ASCENDING), ("source_url", ASCENDING)], name="idx_crawl_detail_run_source"),
        IndexModel([("created_at", ASCENDING)], name="idx_crawl_detail_created_at"),
    ])

    db[STORAGE_TASKS].create_indexes([
        IndexModel([("task_id", ASCENDING)], name="idx_storage_task_id", unique=True),
        IndexModel(
            [("movie_id", ASCENDING), ("info_hash", ASCENDING), ("status", ASCENDING)],
            name="idx_storage_task_dedup",
        ),
        IndexModel([("movie_code", ASCENDING)], name="idx_storage_task_movie_code"),
        IndexModel([("status", ASCENDING)], name="idx_storage_task_status"),
        IndexModel([("created_at", DESCENDING)], name="idx_storage_task_created_at"),
    ])

    db[STORAGE_COUNTERS].create_indexes([
        IndexModel([("_key", ASCENDING)], name="idx_storage_counter_key", unique=True),
    ])
