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


def stop_current_task(run_id: str | None = None) -> bool:
    """Signal the current task to stop. Returns True if a task was running.

    Args:
        run_id: If provided, only stop if this run is the current one.
    """
    if _current_run_id is None:
        return False
    if run_id is not None and _current_run_id != run_id:
        return False
    _stop_event.set()
    return True


def _ensure_worker():
    global _worker_running
    with _worker_lock:
        if not _worker_running:
            _worker_running = True
            thread = threading.Thread(target=_worker_loop, daemon=True)
            thread.start()


def _append_log(run_id: str, message: str, level: str = "INFO"):
    """Append a log entry to the run's log file."""
    from app.run_storage import load_logs, save_logs

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
    }

    try:
        logs = load_logs(run_id)
        logs.append(log_entry)
        save_logs(run_id, logs)
    except Exception as e:
        print(
            f"[ERROR] Failed to append log: {e} "
            f"(run_id={run_id}, msg={message[:100]})",
            file=sys.stderr,
        )


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
        detail_col = get_mongo_db()["run_detail_tasks"]
        repository = MovieRepository()

        runs_col.update_one(
            {"_id": ObjectId(run_id)},
            {"$set": {"status": "running", "started_at": datetime.now(timezone.utc)}},
        )
        _append_log(run_id, "任务开始执行", "INFO")

        stop_requested = False

        try:
            run_doc = runs_col.find_one({"_id": ObjectId(run_id)})
            if not run_doc:
                raise ValueError(f"Run document {run_id} not found")
            task_doc = tasks_col.find_one({"_id": ObjectId(run_doc["task_id"])})
            if not task_doc:
                raise ValueError(f"Task {run_doc['task_id']} not found")

            task = build_crawl_task_from_doc(task_doc)
            _append_log(run_id, f"执行任务: {task.name}, URL: {task.final_url}", "INFO")

            def log_callback(message: str, level: str = "INFO"):
                _append_log(run_id, message, level)

            def on_detail_created(detail_task: dict) -> None:
                detail_col.insert_one({
                    "run_id": run_id,
                    "task_name": task.name,
                    "code": detail_task.get("code"),
                    "source_url": detail_task.get("url"),
                    "source_name": detail_task.get("name"),
                    "status": "pending_crawl",
                    "error": None,
                    "item_data": None,
                    "created_at": datetime.now(timezone.utc),
                    "crawled_at": None,
                    "saved_at": None,
                })

            def on_detail_failed(detail_task: dict, error: str) -> None:
                detail_col.update_one(
                    {"run_id": run_id, "source_url": detail_task.get("url")},
                    {"$set": {
                        "status": "crawl_failed",
                        "error": error,
                        "crawled_at": datetime.now(timezone.utc),
                    }},
                    upsert=True,
                )

            def on_item_saved(detail_task: dict, cleaned_item: dict) -> None:
                try:
                    repository.upsert_movie(cleaned_item)
                    detail_col.update_one(
                        {"run_id": run_id, "source_url": detail_task.get("url")},
                        {"$set": {
                            "status": "saved",
                            "crawled_at": datetime.now(timezone.utc),
                            "saved_at": datetime.now(timezone.utc),
                            "item_data": cleaned_item,
                        }},
                        upsert=True,
                    )
                except Exception as save_exc:
                    detail_col.update_one(
                        {"run_id": run_id, "source_url": detail_task.get("url")},
                        {"$set": {
                            "status": "save_failed",
                            "crawled_at": datetime.now(timezone.utc),
                            "error": str(save_exc),
                            "item_data": cleaned_item,
                        }},
                        upsert=True,
                    )

            service = MovieService()
            result = service.crawl_javdb_task(
                task,
                stop_check=lambda: _stop_event.is_set(),
                log_callback=log_callback,
                on_item_saved=on_item_saved,
                on_detail_created=on_detail_created,
                on_detail_failed=on_detail_failed,
            )

            stop_requested = result.get("stopped", False) or _stop_event.is_set()

            total_detail = detail_col.count_documents({"run_id": run_id})
            saved_count = detail_col.count_documents({"run_id": run_id, "status": "saved"})
            save_failed = detail_col.count_documents({"run_id": run_id, "status": "save_failed"})
            crawl_failed = detail_col.count_documents({"run_id": run_id, "status": "crawl_failed"})

            _append_log(
                run_id,
                f"任务完成: 总计={total_detail}, 已保存={saved_count}, 入库失败={save_failed}, 爬取失败={crawl_failed}",
                "INFO",
            )

            final_status = "stopped" if stop_requested else "completed"

            # 原子条件更新: 仅在状态仍为 "running" 时写入，
            # 防止覆盖已由 stop 端点设置的 "stopped" 状态
            update_result = runs_col.update_one(
                {"_id": ObjectId(run_id), "status": "running"},
                {
                    "$set": {
                        "status": final_status,
                        "finished_at": datetime.now(timezone.utc),
                        "result": {
                            "total_tasks": total_detail,
                            "saved": saved_count,
                            "save_failed": save_failed,
                            "crawl_failed": crawl_failed,
                        },
                    }
                },
            )
            if update_result.modified_count == 0:
                _append_log(run_id, "状态已被外部更新，跳过写入", "WARNING")

        except Exception as exc:
            tb = traceback.format_exc()
            _append_log(run_id, f"错误: {exc}", "ERROR")
            _append_log(run_id, tb, "ERROR")

            error_status = "stopped" if stop_requested else "failed"
            runs_col.update_one(
                {"_id": ObjectId(run_id), "status": "running"},
                {"$set": {
                    "status": error_status,
                    "finished_at": datetime.now(timezone.utc),
                    "error": str(exc) if error_status == "failed" else None,
                }},
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


def retry_detail_task(task_id: str, mode: str) -> dict:
    """重试 detail task 的爬取或入库操作。

    Args:
        task_id: detail task 的 ObjectId 字符串
        mode: "crawl" 或 "save"
    """
    from scraper.database.mongo_client import get_mongo_db
    from scraper.database.repositories.movie_repository import MovieRepository

    detail_col = get_mongo_db()["run_detail_tasks"]
    doc = detail_col.find_one({"_id": ObjectId(task_id)})
    if not doc:
        return {"success": False, "error": "任务不存在"}

    if mode == "crawl":
        detail_col.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {
                "status": "pending_crawl",
                "error": None,
                "crawled_at": None,
                "saved_at": None,
                "item_data": None,
                "retried_at": datetime.now(timezone.utc),
            }},
        )
        return {"success": True, "message": "已标记为待重新爬取，请重新运行任务"}

    elif mode == "save":
        item_data = doc.get("item_data")
        if not item_data:
            return {"success": False, "error": "无数据可入库"}

        repository = MovieRepository()
        try:
            repository.upsert_movie(item_data)
            detail_col.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {"status": "saved", "saved_at": datetime.now(timezone.utc), "error": None}},
            )
            return {"success": True, "message": "重新入库成功"}
        except Exception as e:
            detail_col.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {"status": "save_failed", "error": str(e)}},
            )
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "未知模式"}


def _stringify_objectids(obj: Any) -> Any:
    """Recursively convert all ObjectId instances to strings."""
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _stringify_objectids(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_objectids(item) for item in obj]
    return obj


def run_to_response(doc: dict) -> dict | None:
    """Convert MongoDB doc to JSON-safe response dict. Returns None on failure."""
    try:
        return _stringify_objectids(doc)
    except Exception as e:
        print(
            f"[ERROR] Failed to convert run doc: {e} (keys={list(doc.keys())})",
            file=sys.stderr,
        )
        return None
