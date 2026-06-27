from __future__ import annotations

from datetime import datetime, timezone

from shared.database import get_database
from shared.database.collections import STORAGE_COUNTERS, STORAGE_TASKS


class StorageTaskRepository:
    def __init__(self, db=None, collection=None, counters_collection=None) -> None:
        self._db = db
        self.collection = collection
        self._counters = counters_collection

    @property
    def _database(self):
        if self._db is None:
            self._db = get_database()
        return self._db

    @property
    def counters(self):
        if self._counters is None:
            self._counters = self._database[STORAGE_COUNTERS]
        return self._counters

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self._database[STORAGE_TASKS]
        return self._collection

    @collection.setter
    def collection(self, value):
        self._collection = value

    def create(self, document: dict) -> dict:
        doc = dict(document)
        self.collection.insert_one(doc)
        return doc

    def get_by_task_id(self, task_id: str) -> dict | None:
        return self.collection.find_one({"task_id": task_id})

    def update(self, task_id: str, fields: dict) -> None:
        update = dict(fields)
        update["updated_at"] = datetime.now(timezone.utc)
        self.collection.update_one({"task_id": task_id}, {"$set": update})

    def find_next_executable(self, now) -> dict | None:
        return self.collection.find_one_and_update(
            {"status": "running"},
            {"$set": {"status": "running", "updated_at": now}},
            sort=[("created_at", 1)],
        )

    def find_waiting_download(self, now) -> dict | None:
        return self.collection.find_one_and_update(
            {
                "status": "waiting_download",
                "$or": [
                    {"download.next_poll_at": {"$lte": now}},
                    {"download.next_poll_at": {"$exists": False}},
                    {"progress": {"$gte": 100}},
                ],
            },
            {"$set": {"status": "running", "updated_at": now}},
            sort=[("created_at", 1)],
        )

    def find_waiting_retry(self, now) -> dict | None:
        return self.collection.find_one_and_update(
            {"status": "waiting_retry", "retry.next_retry_at": {"$lte": now}},
            {"$set": {"status": "running", "updated_at": now}},
            sort=[("retry.next_retry_at", 1)],
        )

    def find_pending(self, now) -> dict | None:
        return self.collection.find_one_and_update(
            {"status": "pending"},
            {"$set": {"status": "running", "updated_at": now}},
            sort=[("created_at", 1)],
        )

    def mark_failed(self, task_id: str, failed_step: str, error: dict, retryable: bool) -> None:
        self.update(
            task_id,
            {
                "status": "retryable" if retryable else "failed",
                "step": failed_step,
                "error": error,
                "error_message": error.get("message", ""),
            },
        )

    def mark_completed(self, task_id: str, final_files: list[dict]) -> None:
        self.update(
            task_id,
            {
                "status": "completed",
                "step": None,
                "progress": 1.0,
                "error_message": None,
                "completed_at": datetime.now(timezone.utc),
                "final_files": final_files,
            },
        )

    def get_by_movie_hash_status(self, movie_id: str, info_hash: str, statuses: set[str]) -> dict | None:
        return self.collection.find_one(
            {
                "movie_id": movie_id,
                "info_hash": info_hash,
                "status": {"$in": list(statuses)},
            }
        )
