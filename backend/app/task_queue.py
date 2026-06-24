import io
import threading
import queue
import traceback
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

_Queue = queue.Queue[Any]
_task_queue: _Queue = queue.Queue()
_current_run_id: str | None = None
_worker_running = False
_worker_lock = threading.Lock()


def enqueue_task(task_id: str) -> dict:
    """Add a task to the execution queue. Returns the run document."""
    from scraper.database.mongo_client import get_mongo_db

    tasks_col = get_mongo_db()["config_tasks"]
    task_doc = tasks_col.find_one({"_id": ObjectId(task_id)})

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

    return _run_to_response(run_doc)


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
    except Exception:
        pass


def _worker_loop():
    global _current_run_id, _worker_running

    from scraper.database.mongo_client import get_mongo_db
    from scraper.services.movie_service import MovieService
    from scraper.tasks.task_utils import build_crawl_task_from_doc

    while True:
        run_id = _task_queue.get()
        _current_run_id = run_id

        runs_col = get_mongo_db()["task_runs"]
        tasks_col = get_mongo_db()["config_tasks"]

        runs_col.update_one(
            {"_id": ObjectId(run_id)},
            {"$set": {"status": "running", "started_at": datetime.now(timezone.utc)}},
        )
        _append_log(run_id, "任务开始执行", "INFO")

        try:
            run_doc = runs_col.find_one({"_id": ObjectId(run_id)})
            task_doc = tasks_col.find_one({"_id": ObjectId(run_doc["task_id"])})
            if not task_doc:
                raise ValueError(f"Task {run_doc['task_id']} not found")

            task = build_crawl_task_from_doc(task_doc)
            _append_log(run_id, f"执行任务: {task.name}, URL: {task.final_url}", "INFO")

            service = MovieService()

            # Capture stdout during execution
            captured = io.StringIO()
            import sys
            old_stdout = sys.stdout
            sys.stdout = io.TextIOWrapper(io.BytesIO(), "utf-8")

            # We can't easily capture arbitrary prints, but we can wrap with context
            result = service.crawl_javdb_task(task)

            sys.stdout = old_stdout

            _append_log(
                run_id,
                f"任务完成: total={result.get('total_tasks', 0)}, "
                f"completed={result.get('completed_tasks', 0)}, "
                f"saved={result.get('saved', 0)}",
                "INFO",
            )

            runs_col.update_one(
                {"_id": ObjectId(run_id)},
                {
                    "$set": {
                        "status": "completed",
                        "finished_at": datetime.now(timezone.utc),
                        "result": result,
                    }
                },
            )
        except Exception as exc:
            tb = traceback.format_exc()
            _append_log(run_id, f"错误: {exc}", "ERROR")
            _append_log(run_id, tb, "ERROR")
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
            _task_queue.task_done()


def get_queue_status() -> dict:
    return {
        "queue_size": _task_queue.qsize(),
        "is_running": _current_run_id is not None,
        "current_run_id": _current_run_id,
    }


def _run_to_response(doc: dict) -> dict:
    return {**doc, "_id": str(doc["_id"])}
