from app.db.collections import (
    CRAWL_RUNS,
    CRAWL_RUN_DETAIL_TASKS,
    CRAWL_TASKS,
    MOVIE_MAGNETS,
    STORAGE_COUNTERS,
    STORAGE_TASKS,
)
from app.db.indexes import ensure_backend_indexes


class FakeCollection:
    def __init__(self):
        self.indexes = []

    def create_indexes(self, indexes):
        self.indexes.extend(indexes)


class FakeDb:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        self.collections.setdefault(name, FakeCollection())
        return self.collections[name]


def test_ensure_backend_indexes_creates_indexes_for_fresh_collections():
    db = FakeDb()

    ensure_backend_indexes(db)

    assert CRAWL_TASKS in db.collections
    assert CRAWL_RUNS in db.collections
    assert CRAWL_RUN_DETAIL_TASKS in db.collections
    assert STORAGE_TASKS in db.collections
    assert STORAGE_COUNTERS in db.collections
    assert MOVIE_MAGNETS in db.collections
    assert {idx.document["name"] for idx in db.collections[CRAWL_RUNS].indexes} == {
        "idx_crawl_runs_task_status",
        "idx_crawl_runs_queued_at",
    }
    assert {idx.document["name"] for idx in db.collections[STORAGE_TASKS].indexes} >= {
        "idx_storage_task_id",
        "idx_storage_task_status",
        "idx_storage_task_created_at",
    }
    assert {idx.document["name"] for idx in db.collections[MOVIE_MAGNETS].indexes} >= {
        "idx_movie_magnets_movie_dedupe",
        "idx_movie_magnets_movie_id",
        "idx_movie_magnets_info_hash",
        "idx_movie_magnets_source_task",
    }
