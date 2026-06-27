"""Storage tasks API for CloudDrive2 file operations."""

import logging
import re
from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query

from app.core.bson import stringify_objectids
from app.db.collections import MOVIES, MOVIE_MAGNETS, STORAGE_COUNTERS, STORAGE_TASKS
from app.modules.storage.tasks.id_generator import generate_storage_task_id
from app.modules.storage.tasks.logs import load_storage_task_logs
from scraper.database.mongo_client import get_mongo_db
from scraper.database.repositories.movie_magnet_repository import select_best_magnet as _select_best_magnet

router = APIRouter(prefix="/api/storage/tasks", tags=["storage-tasks"])

TASKS_COLLECTION = STORAGE_TASKS
MOVIES_COLLECTION = MOVIES
COUNTERS_COLLECTION = STORAGE_COUNTERS
MAGNETS_COLLECTION = MOVIE_MAGNETS

# Task statuses that indicate a task is actively in progress or queued
ACTIVE_STATUSES = {"pending", "running", "waiting_download", "waiting_retry", "retryable"}

logger = logging.getLogger("storage_tasks")


def _col():
    return get_mongo_db()[TASKS_COLLECTION]


def _movies_col():
    return get_mongo_db()[MOVIES_COLLECTION]


def _movie_magnets_col():
    return get_mongo_db()[MAGNETS_COLLECTION]


def _counters_col():
    return get_mongo_db()[COUNTERS_COLLECTION]


def _escape_regex(value: str) -> str:
    """Escape regex special characters."""
    return re.escape(value)


def _generate_task_id() -> str:
    return generate_storage_task_id(_counters_col())


def _extract_info_hash(magnet_url: str) -> str:
    """Extract the info_hash (btih) from a magnet URL.

    Returns the 40-char hex hash, or a lowercased copy of whatever
    value follows the ``xt=urn:btih:`` prefix.
    """
    match = re.search(r"xt=urn:btih:([a-zA-Z0-9]+)", magnet_url)
    if match:
        return match.group(1).lower()
    return ""


# ---------------------------------------------------------------------------
# POST /api/storage/tasks/batch-retry — batch retry failed tasks
# ---------------------------------------------------------------------------

@router.post("/batch-retry")
def batch_retry_storage_tasks(body: dict):
    """Retry multiple failed/waiting_retry tasks in batch."""
    task_ids = body.get("task_ids", [])
    if not task_ids:
        raise HTTPException(status_code=400, detail="task_ids is required")
    result = _col().update_many(
        {"task_id": {"$in": task_ids}, "status": {"$in": ["failed", "waiting_retry"]}},
        {"$set": {"status": "pending", "step": None, "error_message": None, "updated_at": datetime.now()}},
    )
    return {"retried": result.modified_count, "skipped": len(task_ids) - result.modified_count}


# ---------------------------------------------------------------------------
# POST /api/storage/tasks/batch-cancel — batch cancel tasks
# ---------------------------------------------------------------------------

@router.post("/batch-cancel")
def batch_cancel_storage_tasks(body: dict):
    """Cancel multiple pending/waiting tasks in batch."""
    task_ids = body.get("task_ids", [])
    if not task_ids:
        raise HTTPException(status_code=400, detail="task_ids is required")
    result = _col().update_many(
        {"task_id": {"$in": task_ids}, "status": {"$in": list(ACTIVE_STATUSES - {"running"})}},
        {"$set": {"status": "cancelled", "updated_at": datetime.now()}},
    )
    return {"cancelled": result.modified_count}


# ---------------------------------------------------------------------------
# POST /api/storage/tasks/batch-delete — batch delete tasks
# ---------------------------------------------------------------------------

@router.post("/batch-delete")
def batch_delete_storage_tasks(body: dict):
    """Batch delete completed/failed/cancelled tasks."""
    task_ids = body.get("task_ids", [])
    if not task_ids:
        raise HTTPException(status_code=400, detail="task_ids is required")
    result = _col().delete_many(
        {"task_id": {"$in": task_ids}, "status": {"$in": ["completed", "failed", "cancelled", "retryable"]}},
    )
    return {"deleted": result.deleted_count}


# ---------------------------------------------------------------------------
# POST /api/storage/tasks — create a single task
# ---------------------------------------------------------------------------

@router.post("")
def create_storage_task(body: dict):
    """Create a storage task for a single movie.

    Request body:
        { "movie_id": "...", "magnet_url": "magnet:..." }
    """
    movie_id = body.get("movie_id")
    magnet_url = body.get("magnet_url")

    if not movie_id:
        raise HTTPException(status_code=400, detail="movie_id is required")
    if not magnet_url:
        raise HTTPException(status_code=400, detail="magnet_url is required")

    # Validate movie_id
    try:
        movie_oid = ObjectId(movie_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid movie_id")

    # Look up movie
    movie = _movies_col().find_one({"_id": movie_oid})
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    info_hash = _extract_info_hash(magnet_url)

    # Check for duplicate: same movie_id + info_hash + active status
    if info_hash:
        existing = _col().find_one({
            "movie_id": str(movie_oid),
            "info_hash": info_hash,
            "status": {"$in": list(ACTIVE_STATUSES)},
        })
        if existing:
            return {"task_id": existing["task_id"], "status": "existing"}

    # Generate task_id
    task_id = _generate_task_id()
    now = datetime.now()

    movie_code = movie.get("code") or movie.get("config_task_name", "")

    task_doc = {
        "task_id": task_id,
        "movie_id": str(movie_oid),
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

    _col().insert_one(task_doc)

    # Update movie's storage_summary
    _movies_col().update_one(
        {"_id": movie_oid},
        {"$set": {
            "storage_summary.last_task_id": task_id,
            "storage_summary.last_status": "pending",
            "storage_summary.updated_at": now,
        }},
    )

    return {"task_id": task_id, "status": "created"}


# ---------------------------------------------------------------------------
# POST /api/storage/tasks/batch — create tasks for multiple movies
# ---------------------------------------------------------------------------

@router.post("/batch")
def batch_create_storage_tasks(body: dict):
    """Create storage tasks for multiple movies in batch.

    Request body:
        {
            "movie_ids": ["id1", "id2", ...],
            "skip_running": true,
            "skip_completed": true,
            "retry_failed": false
        }
    """
    movie_ids = body.get("movie_ids", [])
    if not movie_ids:
        raise HTTPException(status_code=400, detail="movie_ids is required")

    skip_running = body.get("skip_running", True)
    skip_completed = body.get("skip_completed", True)
    retry_failed = body.get("retry_failed", False)

    # Validate all IDs upfront
    movie_oids = []
    for mid in movie_ids:
        try:
            movie_oids.append(ObjectId(mid))
        except InvalidId:
            raise HTTPException(status_code=400, detail=f"Invalid movie_id: {mid}")

    # Fetch all movies in one query
    movies = {
        str(doc["_id"]): doc
        for doc in _movies_col().find({"_id": {"$in": movie_oids}})
    }

    requested = len(movie_ids)
    created = 0
    skipped = 0
    items = []

    for mid in movie_ids:
        movie = movies.get(mid)
        if not movie:
            items.append({"movie_id": mid, "result": "skipped", "reason": "movie_not_found"})
            skipped += 1
            continue

        magnets = list(_movie_magnets_col().find({"movie_id": mid}))
        best_magnet = _select_best_magnet(magnets)

        # Fallback: singular "magnet" field (string) when "magnets" array is empty
        if not best_magnet:
            single_magnet = movie.get("magnet", "")
            if single_magnet:
                magnet_url = single_magnet
            else:
                items.append({"movie_id": mid, "result": "skipped", "reason": "no_magnet"})
                skipped += 1
                continue
        else:
            magnet_url = best_magnet.get("magnet") or best_magnet.get("magnet_url") or ""
        info_hash = _extract_info_hash(magnet_url)

        # Check existing tasks for this movie + magnet
        if info_hash:
            existing = _col().find_one({
                "movie_id": mid,
                "info_hash": info_hash,
            })

            if existing:
                existing_status = existing.get("status", "")

                # Already active — skip
                if skip_running and existing_status in ACTIVE_STATUSES:
                    items.append({
                        "movie_id": mid,
                        "result": "skipped",
                        "reason": "already_active",
                        "task_id": existing["task_id"],
                    })
                    skipped += 1
                    continue

                # Already completed — skip
                if skip_completed and existing_status == "completed":
                    items.append({
                        "movie_id": mid,
                        "result": "skipped",
                        "reason": "already_completed",
                        "task_id": existing["task_id"],
                    })
                    skipped += 1
                    continue

                # Failed and retry not requested — skip
                if existing_status == "failed" and not retry_failed:
                    items.append({
                        "movie_id": mid,
                        "result": "skipped",
                        "reason": "previously_failed",
                        "task_id": existing["task_id"],
                    })
                    skipped += 1
                    continue

                # Retry failed: update existing task to pending
                if existing_status == "failed" and retry_failed:
                    now = datetime.now()
                    _col().update_one(
                        {"_id": existing["_id"]},
                        {"$set": {
                            "status": "pending",
                            "step": None,
                            "error_message": None,
                            "progress": 0.0,
                            "updated_at": now,
                        }},
                    )
                    _movies_col().update_one(
                        {"_id": ObjectId(mid)},
                        {"$set": {
                            "storage_summary.last_task_id": existing["task_id"],
                            "storage_summary.last_status": "pending",
                            "storage_summary.updated_at": now,
                        }},
                    )
                    items.append({
                        "movie_id": mid,
                        "result": "retried",
                        "task_id": existing["task_id"],
                    })
                    created += 1
                    continue

        # Create new task
        task_id = _generate_task_id()
        now = datetime.now()
        movie_code = movie.get("code") or movie.get("config_task_name", "")

        task_doc = {
            "task_id": task_id,
            "movie_id": mid,
            "movie_code": movie_code,
            "title": movie.get("source_name") or movie.get("config_task_name", ""),
            "magnet_url": magnet_url,
            "info_hash": info_hash,
            "status": "pending",
            "step": None,
            "source": "batch",
            "retry_count": 0,
            "max_retries": 3,
            "error_message": None,
            "download_path": None,
            "target_path": None,
            "progress": 0.0,
            "created_at": now,
            "updated_at": now,
        }

        _col().insert_one(task_doc)

        _movies_col().update_one(
            {"_id": ObjectId(mid)},
            {"$set": {
                "storage_summary.last_task_id": task_id,
                "storage_summary.last_status": "pending",
                "storage_summary.updated_at": now,
            }},
        )

        items.append({"movie_id": mid, "result": "created", "task_id": task_id})
        created += 1

    return {
        "requested": requested,
        "created": created,
        "skipped": skipped,
        "items": items,
    }


# ---------------------------------------------------------------------------
# GET /api/storage/tasks — list with filters
# ---------------------------------------------------------------------------

@router.get("")
def list_storage_tasks(
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    step: str | None = Query(default=None),
    source: str | None = Query(default=None),
    date_from: str | None = Query(default=None, description="YYYY-MM-DD"),
    date_to: str | None = Query(default=None, description="YYYY-MM-DD"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List storage tasks with optional filters and pagination."""
    query: dict = {}

    if search:
        escaped = _escape_regex(search)
        query["$or"] = [
            {"movie_code": {"$regex": escaped, "$options": "i"}},
            {"title": {"$regex": escaped, "$options": "i"}},
            {"task_id": {"$regex": escaped, "$options": "i"}},
        ]

    if status:
        query["status"] = status

    if step:
        query["step"] = step

    if source:
        query["source"] = source

    if date_from or date_to:
        created_at_filter: dict = {}
        if date_from:
            created_at_filter["$gte"] = datetime.strptime(date_from, "%Y-%m-%d")
        if date_to:
            created_at_filter["$lte"] = datetime.strptime(date_to, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
        query["created_at"] = created_at_filter

    total = _col().count_documents(query)
    total_pages = max(1, (total + limit - 1) // limit)

    cursor = (
        _col()
        .find(query)
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )

    items = [stringify_objectids(doc) for doc in cursor]

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


# ---------------------------------------------------------------------------
# GET /api/storage/tasks/stats — aggregate task counts by status
# ---------------------------------------------------------------------------

@router.get("/stats")
def get_storage_task_stats():
    """Return task counts grouped by status."""
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    results = {doc["_id"]: doc["count"] for doc in _col().aggregate(pipeline)}
    return {
        "pending": results.get("pending", 0),
        "waiting_download": results.get("waiting_download", 0),
        "running": results.get("running", 0),
        "waiting_retry": results.get("waiting_retry", 0),
        "failed": results.get("failed", 0),
        "completed": results.get("completed", 0),
    }


# ---------------------------------------------------------------------------
# GET /api/storage/tasks/{task_id} — task detail
# ---------------------------------------------------------------------------

@router.get("/{task_id}")
def get_storage_task(task_id: str):
    """Get full detail for a single storage task."""
    doc = _col().find_one({"task_id": task_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Task not found")
    return stringify_objectids(doc)


# ---------------------------------------------------------------------------
# GET /api/storage/tasks/{task_id}/logs — read JSONL logs
# ---------------------------------------------------------------------------

@router.get("/{task_id}/logs")
def get_storage_task_logs(task_id: str):
    """Read execution logs from run_data/storage_tasks/{task_id}.jsonl."""
    # Verify the task exists
    doc = _col().find_one({"task_id": task_id}, {"task_id": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"logs": load_storage_task_logs(task_id)}


# ---------------------------------------------------------------------------
# POST /api/storage/tasks/{task_id}/retry — reset failed task to pending
# ---------------------------------------------------------------------------

@router.post("/{task_id}/retry")
def retry_storage_task(task_id: str):
    """Reset a failed or waiting_retry task back to pending."""
    result = _col().update_one(
        {"task_id": task_id, "status": {"$in": ["failed", "waiting_retry", "retryable", "stopped"]}},
        {"$set": {"status": "pending", "step": None, "error_message": None, "updated_at": datetime.now()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found or not retryable")
    return {"status": "retried"}


# ---------------------------------------------------------------------------
# POST /api/storage/tasks/{task_id}/cancel — cancel pending/waiting task
# ---------------------------------------------------------------------------

@router.post("/{task_id}/cancel")
def cancel_storage_task(task_id: str):
    """Cancel a pending or waiting task (not running)."""
    result = _col().update_one(
        {"task_id": task_id, "status": {"$in": list(ACTIVE_STATUSES - {"running"})}},
        {"$set": {"status": "cancelled", "updated_at": datetime.now()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
    return {"status": "cancelled"}


# ---------------------------------------------------------------------------
# DELETE /api/storage/tasks/{task_id} — delete completed/failed/cancelled task
# ---------------------------------------------------------------------------

@router.delete("/{task_id}")
def delete_storage_task(task_id: str):
    """Delete a completed, failed, or cancelled task."""
    result = _col().delete_one(
        {"task_id": task_id, "status": {"$in": ["completed", "failed", "cancelled"]}},
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found or not deletable")
    return {"status": "deleted"}
