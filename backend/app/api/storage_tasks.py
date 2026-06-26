"""Storage tasks API for CloudDrive2 file operations."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query

from scraper.config.settings import RUN_DATA_DIR
from scraper.database.mongo_client import get_mongo_db

router = APIRouter(prefix="/api/storage/tasks", tags=["storage-tasks"])

TASKS_COLLECTION = "storage_tasks"
MOVIES_COLLECTION = "movies"
COUNTERS_COLLECTION = "storage_counters"

# Task statuses that indicate a task is actively in progress or queued
ACTIVE_STATUSES = {"pending", "running", "waiting_download", "waiting_retry", "retryable"}

logger = logging.getLogger("storage_tasks")


def _col():
    return get_mongo_db()[TASKS_COLLECTION]


def _movies_col():
    return get_mongo_db()[MOVIES_COLLECTION]


def _counters_col():
    return get_mongo_db()[COUNTERS_COLLECTION]


def _stringify_objectids(obj):
    """Recursively convert all ObjectId instances to strings."""
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _stringify_objectids(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_objectids(item) for item in obj]
    return obj


def _escape_regex(value: str) -> str:
    """Escape regex special characters."""
    return re.escape(value)


def _generate_task_id() -> str:
    """Generate a unique task ID: storage_{YYYYMMDD}_{HHmmss}_{counter}.

    Uses an atomic counter in MongoDB to guarantee uniqueness even under
    concurrent requests within the same second.
    """
    now = datetime.now()
    date_part = now.strftime("%Y%m%d")
    time_part = now.strftime("%H%M%S")
    prefix = f"storage_{date_part}_{time_part}"

    # Atomic increment on a per-second counter document
    result = _counters_col().find_one_and_update(
        {"_key": prefix},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    counter = result["seq"]

    return f"{prefix}_{counter}"


def _extract_info_hash(magnet_url: str) -> str:
    """Extract the info_hash (btih) from a magnet URL.

    Returns the 40-char hex hash, or a lowercased copy of whatever
    value follows the ``xt=urn:btih:`` prefix.
    """
    match = re.search(r"xt=urn:btih:([a-zA-Z0-9]+)", magnet_url)
    if match:
        return match.group(1).lower()
    return ""


def _select_best_magnet(magnets: list[dict]) -> dict | None:
    """Pick the best magnet from a movie's magnet list.

    Preference order:
    1. Has Chinese subtitle indicator (chs / ch / cht / chinese in title)
    2. Largest file size
    """
    if not magnets:
        return None

    def _parse_size_mb(size_str: str) -> float:
        """Parse a human-readable size string (e.g. '4.5 GB') into MB."""
        if not size_str:
            return 0.0
        size_str = size_str.strip().upper()
        match = re.match(r"([\d.]+)\s*(GB|MB|KB|TB)?", size_str)
        if not match:
            return 0.0
        value = float(match.group(1))
        unit = match.group(2) or "MB"
        multipliers = {"KB": 1 / 1024, "MB": 1, "GB": 1024, "TB": 1024 * 1024}
        return value * multipliers.get(unit, 1)

    def _has_chinese_sub(magnet: dict) -> bool:
        title = (magnet.get("title") or "").lower()
        return any(kw in title for kw in ["chs", "cht", "chinese", "中字", "中文", "字幕"])

    # Sort: chinese-sub first, then largest size
    scored = []
    for m in magnets:
        if not isinstance(m, dict) or not m.get("magnet"):
            continue
        scored.append((_has_chinese_sub(m), _parse_size_mb(m.get("size", "")), m))

    if not scored:
        return None

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return scored[0][2]


def _storage_log_path(task_id: str) -> Path:
    """Return path: RUN_DATA_DIR/storage/{task_id}.jsonl"""
    return RUN_DATA_DIR / "storage" / f"{task_id}.jsonl"


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

    movie_code = movie.get("code") or movie.get("name", "")

    task_doc = {
        "task_id": task_id,
        "movie_id": str(movie_oid),
        "movie_code": movie_code,
        "title": movie.get("title") or movie.get("name", ""),
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

        magnets = movie.get("magnets", [])
        best_magnet = _select_best_magnet(magnets)
        if not best_magnet:
            items.append({"movie_id": mid, "result": "skipped", "reason": "no_magnet"})
            skipped += 1
            continue

        magnet_url = best_magnet.get("magnet", "")
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
        movie_code = movie.get("code") or movie.get("name", "")

        task_doc = {
            "task_id": task_id,
            "movie_id": mid,
            "movie_code": movie_code,
            "title": movie.get("title") or movie.get("name", ""),
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

    items = [_stringify_objectids(doc) for doc in cursor]

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
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
    return _stringify_objectids(doc)


# ---------------------------------------------------------------------------
# GET /api/storage/tasks/{task_id}/logs — read JSONL logs
# ---------------------------------------------------------------------------

@router.get("/{task_id}/logs")
def get_storage_task_logs(task_id: str):
    """Read execution logs from run_data/storage/{task_id}.jsonl."""
    # Verify the task exists
    doc = _col().find_one({"task_id": task_id}, {"task_id": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Task not found")

    log_path = _storage_log_path(task_id)
    if not log_path.exists():
        return {"logs": []}

    entries = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except json.JSONDecodeError as e:
        logger.warning("Corrupted log file for task %s: %s", task_id, e)
        raise HTTPException(status_code=500, detail="Corrupted log file")

    return {"logs": entries}
