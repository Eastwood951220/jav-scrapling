from pymongo import ASCENDING, DESCENDING, IndexModel

from shared.database.collections.storage import STORAGE_COUNTERS, STORAGE_TASKS

STORAGE_TASK_INDEXES: list[IndexModel] = [
    IndexModel([("task_id", ASCENDING)], name="idx_storage_task_id", unique=True),
    IndexModel([("movie_id", ASCENDING), ("info_hash", ASCENDING), ("status", ASCENDING)], name="idx_storage_task_dedup"),
    IndexModel([("movie_code", ASCENDING)], name="idx_storage_task_movie_code"),
    IndexModel([("status", ASCENDING)], name="idx_storage_task_status"),
    IndexModel([("created_at", DESCENDING)], name="idx_storage_task_created_at"),
]

STORAGE_COUNTER_INDEXES: list[IndexModel] = [
    IndexModel([("_key", ASCENDING)], name="idx_storage_counter_key", unique=True),
]


def ensure_storage_indexes(db) -> None:
    db[STORAGE_TASKS].create_indexes(STORAGE_TASK_INDEXES)
    db[STORAGE_COUNTERS].create_indexes(STORAGE_COUNTER_INDEXES)
