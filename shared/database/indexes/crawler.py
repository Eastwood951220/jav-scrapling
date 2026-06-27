from pymongo import ASCENDING, DESCENDING, IndexModel

from shared.database.collections.crawler import CRAWL_RUNS, CRAWL_RUN_DETAIL_TASKS, CRAWL_TASKS

CRAWL_TASK_INDEXES: list[IndexModel] = [
    IndexModel([("created_at", DESCENDING)], name="idx_crawl_tasks_created_at"),
    IndexModel([("name", ASCENDING)], name="idx_crawl_tasks_name"),
]

CRAWL_RUN_INDEXES: list[IndexModel] = [
    IndexModel([("task_id", ASCENDING), ("status", ASCENDING)], name="idx_crawl_runs_task_status"),
    IndexModel([("queued_at", DESCENDING)], name="idx_crawl_runs_queued_at"),
]

CRAWL_RUN_DETAIL_INDEXES: list[IndexModel] = [
    IndexModel([("run_id", ASCENDING), ("status", ASCENDING)], name="idx_crawl_detail_run_status"),
    IndexModel([("run_id", ASCENDING), ("source_url", ASCENDING)], name="idx_crawl_detail_run_source"),
    IndexModel([("created_at", ASCENDING)], name="idx_crawl_detail_created_at"),
]


def ensure_crawler_indexes(db) -> None:
    db[CRAWL_TASKS].create_indexes(CRAWL_TASK_INDEXES)
    db[CRAWL_RUNS].create_indexes(CRAWL_RUN_INDEXES)
    db[CRAWL_RUN_DETAIL_TASKS].create_indexes(CRAWL_RUN_DETAIL_INDEXES)
