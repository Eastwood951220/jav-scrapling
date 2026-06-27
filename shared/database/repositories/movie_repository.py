from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from shared.database import get_database
from shared.database.collections import MOVIES


class MovieRepository:
    def __init__(self, db=None, collection=None) -> None:
        self.collection = collection if collection is not None else (db or get_database())[MOVIES]

    def get_by_id(self, movie_id: str) -> dict | None:
        try:
            oid = ObjectId(movie_id)
        except (InvalidId, TypeError):
            return None
        return self.collection.find_one({"_id": oid})

    def update_storage_summary(
        self,
        movie_id: str,
        task_id: str,
        status: str,
        current_step: str | None = None,
        final_files: list[dict] | None = None,
    ) -> None:
        try:
            oid = ObjectId(movie_id)
        except (InvalidId, TypeError):
            return

        fields = {
            "storage_summary.last_task_id": task_id,
            "storage_summary.last_status": status,
            "storage_summary.updated_at": datetime.now(timezone.utc),
        }
        if current_step is not None:
            fields["storage_summary.current_step"] = current_step
        if final_files is not None:
            fields["storage_summary.locations"] = final_files
        elif status == "completed":
            fields["storage_summary.locations"] = []

        self.collection.update_one({"_id": oid}, {"$set": fields})
