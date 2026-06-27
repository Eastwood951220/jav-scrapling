from __future__ import annotations

import re
from datetime import datetime, timezone

from app.modules.storage.tasks.id_generator import generate_storage_task_id
from shared.database.repositories.magnet_repository import select_best_magnet

ACTIVE_STATUSES = {"pending", "running", "waiting_download", "waiting_retry", "retryable"}


def extract_info_hash(magnet_url: str) -> str:
    match = re.search(r"xt=urn:btih:([a-zA-Z0-9]+)", magnet_url)
    return match.group(1).lower() if match else ""


class StorageTaskService:
    def __init__(self, task_repository, movie_repository, magnet_repository) -> None:
        self.task_repository = task_repository
        self.movie_repository = movie_repository
        self.magnet_repository = magnet_repository

    def create_task(self, body: dict) -> dict:
        movie_id = body.get("movie_id")
        magnet_url = body.get("magnet_url")
        if not movie_id:
            raise ValueError("movie_id is required")
        if not magnet_url:
            raise ValueError("magnet_url is required")

        movie = self.movie_repository.get_by_id(movie_id)
        if not movie:
            raise LookupError("Movie not found")

        info_hash = extract_info_hash(magnet_url)
        existing_getter = getattr(self.task_repository, "get_by_movie_hash_status", None)
        if info_hash and callable(existing_getter):
            existing = existing_getter(movie_id, info_hash, ACTIVE_STATUSES)
            if existing:
                return {"task_id": existing["task_id"], "status": "existing"}

        task_id = self._generate_task_id()
        now = datetime.now(timezone.utc)
        movie_code = movie.get("code") or movie.get("config_task_name", "")
        task_doc = {
            "task_id": task_id,
            "movie_id": movie_id,
            "movie_code": movie_code,
            "title": movie.get("source_name") or movie.get("config_task_name", ""),
            "magnet_url": magnet_url,
            "info_hash": info_hash,
            "status": "pending",
            "step": None,
            "source": "api",
            "retry_count": 0,
            "max_retries": 3,
            "error_message": None,
            "download_path": None,
            "target_path": None,
            "progress": 0.0,
            "created_at": now,
            "updated_at": now,
        }
        self.task_repository.create(task_doc)
        self.movie_repository.update_storage_summary(movie_id, task_id, "pending")
        return {"task_id": task_id, "status": "created"}

    def batch_retry(self, task_ids: list[str]) -> dict:
        if not task_ids:
            raise ValueError("task_ids is required")
        result = self.task_repository.collection.update_many(
            {"task_id": {"$in": task_ids}, "status": {"$in": ["failed", "waiting_retry"]}},
            {"$set": {"status": "pending", "step": None, "error_message": None, "updated_at": datetime.now(timezone.utc)}},
        )
        return {"retried": result.modified_count, "skipped": len(task_ids) - result.modified_count}

    def _generate_task_id(self) -> str:
        return generate_storage_task_id(self.task_repository.counters)
