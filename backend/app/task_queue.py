import os
import sys
import threading
import queue
import traceback
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

_Queue = queue.Queue[Any]
_task_queue: _Queue = queue.Queue()
_current_run_id: str | None = None
_worker_running = False
_worker_lock = threading.Lock()
_stop_event = threading.Event()


def enqueue_task(task_id: str) -> dict:
    """Add a task to the execution queue. Returns the run document."""
    from scraper.database.mongo_client import get_mongo_db

    try:
        oid = ObjectId(task_id)
    except InvalidId:
        raise ValueError(f"Invalid task ID: {task_id}")

    tasks_col = get_mongo_db()["config_tasks"]
    task_doc = tasks_col.find_one({"_id": oid})

    run_doc = {
        "task_id": task_id,
        "task_name": task_doc["name"] if task_doc else None,
        "status": "queued",
        "queued_at": datetime.now(timezone.utc),
        "started_at": None,
        "finished_at": None,
        "result": None,
        "error": None,
        "logs": [],
    }

    result = get_mongo_db()["task_runs"].insert_one(run_doc)
    run_doc["_id"] = str(result.inserted_id)

    _task_queue.put(str(result.inserted_id))
    _ensure_worker()

    return run_to_response(run_doc)


def stop_current_task() -> bool:
    """Signal the current task to stop. Returns True if a task was running."""
    if _current_run_id is not None:
        _stop_event.set()
        return True
    return False


def _ensure_worker():
    global _worker_running
    with _worker_lock:
        if not _worker_running:
            _worker_running = True
            thread = threading.Thread(target=_worker_loop, daemon=True)
            thread.start()


def _append_log(run_id: str, message: str, level: str = "INFO"):
    """Append a log entry to the run document."""
    from scraper.database.mongo_client import get_mongo_db

    try:
        get_mongo_db()["task_runs"].update_one(
            {"_id": ObjectId(run_id)},
            {
                "$push": {
                    "logs": {
                        "timestamp": datetime.now(timezone.utc),
                        "level": level,
                        "message": message,
                    }
                }
            },
        )
    except Exception as e:
        print(f"Failed to append log: {e}", file=sys.stderr)


def _batch_save_items(items: list[dict], batch_size: int, repository) -> int:
    """Persist items in batches, logging progress. Returns total saved count."""
    saved = 0
    total = len(items)

    for i in range(0, total, batch_size):
        batch = items[i:i + batch_size]
        for item in batch:
            if repository.upsert_movie(item):
                saved += 1
        print(f"[DB] batch saved {min(i + batch_size, total)}/{total}, saved={saved}")

    return saved


def _worker_loop():
    global _current_run_id, _worker_running, _stop_event

    from scraper.database.mongo_client import get_mongo_db
    from scraper.database.repositories.movie_repository import MovieRepository
    from scraper.services.movie_service import MovieService
    from scraper.tasks.task_utils import build_crawl_task_from_doc

    while True:
        run_id = _task_queue.get()
        _current_run_id = run_id
        _stop_event.clear()

        runs_col = get_mongo_db()["task_runs"]
        tasks_col = get_mongo_db()["config_tasks"]
        repository = MovieRepository()

        runs_col.update_one(
            {"_id": ObjectId(run_id)},
            {"$set": {"status": "running", "started_at": datetime.now(timezone.utc)}},
        )
        _append_log(run_id, "任务开始执行", "INFO")

        stop_requested = False
        collected_items: list[dict] = []

        try:
            run_doc = runs_col.find_one({"_id": ObjectId(run_id)})
            if not run_doc:
                raise ValueError(f"Run document {run_id} not found")
            task_doc = tasks_col.find_one({"_id": ObjectId(run_doc["task_id"])})
            if not task_doc:
                raise ValueError(f"Task {run_doc['task_id']} not found")

            task = build_crawl_task_from_doc(task_doc)
            _append_log(run_id, f"执行任务: {task.name}, URL: {task.final_url}", "INFO")

            service = MovieService()
            result = service.crawl_javdb_task(
                task,
                stop_check=lambda: _stop_event.is_set(),
            )

            collected_items = result.get("items", [])
            stop_requested = result.get("stopped", False)

            batch_size = int(os.getenv("BATCH_SAVE_SIZE", "50"))
            saved = _batch_save_items(collected_items, batch_size, repository)
            result = {**result, "saved": saved}

            _append_log(
                run_id,
                f"任务完成: total={result.get('total_tasks', 0)}, "
                f"completed={result.get('completed_tasks', 0)}, "
                f"saved={saved}",
                "INFO",
            )

            final_status = "stopped" if _stop_event.is_set() else "completed"
            runs_col.update_one(
                {"_id": ObjectId(run_id)},
                {
                    "$set": {
                        "status": final_status,
                        "finished_at": datetime.now(timezone.utc),
                        "result": result,
                    }
                },
            )
        except Exception as exc:
            tb = traceback.format_exc()
            _append_log(run_id, f"错误: {exc}", "ERROR")
            _append_log(run_id, tb, "ERROR")

            # Drain collected items on crash
            if collected_items:
                try:
                    batch_size = int(os.getenv("BATCH_SAVE_SIZE", "50"))
                    saved = _batch_save_items(collected_items, batch_size, repository)
                    _append_log(run_id, f"崩溃前已保存 {saved} 条数据", "WARN")
                except Exception as save_exc:
                    _append_log(run_id, f"保存崩溃数据失败: {save_exc}", "ERROR")

            runs_col.update_one(
                {"_id": ObjectId(run_id)},
                {
                    "$set": {
                        "status": "failed",
                        "finished_at": datetime.now(timezone.utc),
                        "error": str(exc),
                    }
                },
            )
        finally:
            _current_run_id = None
            _stop_event.clear()
            _task_queue.task_done()



def get_queue_status() -> dict:
    return {
        "queue_size": _task_queue.qsize(),
        "is_running": _current_run_id is not None,
        "current_run_id": _current_run_id,
        "stop_requested": _stop_event.is_set(),
    }


def run_to_response(doc: dict) -> dict:
    return {**doc, "_id": str(doc["_id"])}
