"""Storage worker — compatibility wrapper.

Creates a singleton StorageWorker from shared dependencies and exposes the
original public API: start_storage_worker, stop_storage_worker, get_worker_status.

Also re-exports internal helpers for backward compatibility with existing tests.
These will be removed once tests are migrated to the new step class API.
"""

import sys
from datetime import datetime, timezone
from pathlib import PurePosixPath

from app.core.dependencies import (
    get_clouddrive_client_factory,
    get_magnet_repository,
    get_movie_repository,
    get_storage_config_repository,
    get_storage_task_repository,
)
from app.modules.storage.worker.runner import StorageWorker
from app.modules.storage.worker.state_machine import StorageStateMachine
from app.modules.storage.worker.steps.cleanup_files import CleanupFilesStep
from app.modules.storage.worker.steps.move_files import MoveFilesStep
from app.modules.storage.worker.steps.prepare import PrepareStep
from app.modules.storage.worker.steps.rename_files import RenameFilesStep
from app.modules.storage.worker.steps.scan_files import ScanFilesStep
from app.modules.storage.worker.steps.select_videos import SelectVideosStep
from app.modules.storage.worker.steps.submit_magnet import SubmitMagnetStep
from app.modules.storage.worker.steps.verify_result import VerifyResultStep
from app.modules.storage.worker.steps.wait_download import WaitDownloadStep

from app.modules.storage.tasks.logs import append_storage_task_log
from shared.database import get_database
from shared.database.collections import MOVIES, STORAGE_CONFIG, STORAGE_TASKS
from shared.integrations.storage_providers.clouddrive2.exceptions import CloudDriveOperationError
from shared.integrations.storage_providers.clouddrive2.factory import CloudDriveClientFactory
from shared.integrations.storage_providers.clouddrive2.gateway import CloudDrive2Gateway

# ---------------------------------------------------------------------------
# Singleton worker
# ---------------------------------------------------------------------------

_worker = StorageWorker(
    task_repository=get_storage_task_repository(),
    movie_repository=get_movie_repository(),
    magnet_repository=get_magnet_repository(),
    config_repository=get_storage_config_repository(),
    provider_factory=get_clouddrive_client_factory(),
    state_machine=StorageStateMachine([
        PrepareStep(),
        SubmitMagnetStep(),
        WaitDownloadStep(),
        ScanFilesStep(),
        SelectVideosStep(),
        RenameFilesStep(),
        MoveFilesStep(),
        VerifyResultStep(),
        CleanupFilesStep(),
    ]),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_storage_worker() -> None:
    """Start the storage worker thread if not already running."""
    _worker.start()


def stop_storage_worker() -> None:
    """Signal the worker to stop. Blocks briefly for graceful shutdown."""
    _worker.stop()


def get_worker_status() -> dict:
    """Return current worker status."""
    return {
        "is_running": bool(_worker.thread and _worker.thread.is_alive()),
        "current_task_id": _worker.current_task_id,
        "stop_requested": _worker.stop_event.is_set(),
    }


# ---------------------------------------------------------------------------
# Backward-compatible re-exports for existing tests
# ---------------------------------------------------------------------------

TASKS_COLLECTION = STORAGE_TASKS
MOVIES_COLLECTION = MOVIES
CONFIG_COLLECTION = STORAGE_CONFIG
CONFIG_KEY = {"_key": "default"}


def _append_log(task_id: str, message: str, level: str = "INFO", step: str | None = None) -> None:
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "step": step,
        "message": message,
    }
    try:
        append_storage_task_log(task_id, log_entry)
    except Exception as e:
        print(f"[ERROR] Failed to append storage log: {e} (task_id={task_id})", file=sys.stderr)


def _tasks_col():
    return get_database()[TASKS_COLLECTION]


def _movies_col():
    return get_database()[MOVIES_COLLECTION]


def _config_col():
    return get_database()[CONFIG_COLLECTION]


def _update_task(task_id: str, update: dict) -> None:
    update["updated_at"] = datetime.now(timezone.utc)
    _tasks_col().update_one({"task_id": task_id}, {"$set": update})


def _update_movie_summary(
    movie_id: str,
    task_id: str,
    status: str,
    moved_files: list[dict] | None = None,
) -> None:
    from bson import ObjectId
    from bson.errors import InvalidId

    try:
        oid = ObjectId(movie_id)
    except (InvalidId, TypeError):
        return

    update_fields: dict = {
        "storage_summary.last_task_id": task_id,
        "storage_summary.last_status": status,
        "storage_summary.updated_at": datetime.now(timezone.utc),
    }

    if moved_files is not None:
        locations: list[dict] = []
        for f in moved_files:
            moved_path = f.get("moved_path")
            if moved_path:
                parent = PurePosixPath(moved_path).parent.as_posix()
                locations.append({"path": moved_path, "target_folder": parent})
            for cp in f.get("copied_paths", []):
                parent = PurePosixPath(cp).parent.as_posix()
                locations.append({"path": cp, "target_folder": parent})
        update_fields["storage_summary.locations"] = locations
    elif status == "completed":
        update_fields["storage_summary.locations"] = []

    _movies_col().update_one({"_id": oid}, {"$set": update_fields})


def _build_cd2_client(config: dict):
    factory = CloudDriveClientFactory()
    return factory.create(config)


def _file_to_dict(f) -> dict:
    # Support both protobuf objects (fullPathName/isDirectory) and RemoteFile (full_path/is_directory)
    name = getattr(f, "name", "")
    path = getattr(f, "fullPathName", None) or getattr(f, "full_path", None) or name
    size = getattr(f, "size", 0)
    is_dir = getattr(f, "isDirectory", None)
    if is_dir is None:
        is_dir = getattr(f, "is_directory", False)
    return {"name": name, "path": path, "size": size, "is_dir": bool(is_dir)}


def _is_duplicate_magnet_error(error: Exception) -> bool:
    if not isinstance(error, CloudDriveOperationError):
        return False
    details = str(error)
    return "10008" in details or "任务已存在" in details


def _find_existing_download(cd2, download_root: str, task_id: str) -> list[dict]:
    found_files = []
    try:
        entries = [_file_to_dict(f) for f in cd2.list_sub_files(download_root)]
        for entry in entries:
            if entry.get("is_dir"):
                try:
                    sub_files = [_file_to_dict(f) for f in cd2.list_sub_files(entry["path"])]
                    found_files.extend([f for f in sub_files if not f.get("is_dir")])
                except Exception:
                    pass
            else:
                found_files.append(entry)
    except Exception:
        pass
    return found_files


def _step_submit_magnet(task: dict, config: dict) -> dict:
    """Legacy submit_magnet step — uses raw client for task_name extraction."""
    import grpc

    task_id = task["task_id"]
    magnet_url = task["magnet_url"]
    download_path = task["download_path"]

    cd2 = _build_cd2_client(config)
    try:
        try:
            cd2.create_folder(download_path)
        except Exception:
            pass

        try:
            result = cd2.add_offline_download(magnet_url, download_path)
            cd2_task_name = getattr(result, "taskName", "") or getattr(result, "task_name", "")

            _update_task(task_id, {
                "download.cd2_task_name": cd2_task_name,
                "download.submitted_at": datetime.now(timezone.utc),
                "download.status": "submitted",
            })
            _append_log(task_id, f"磁力链接已提交: task_name={cd2_task_name}", step="submit_magnet")

            return {**task, "download": {
                "cd2_task_name": cd2_task_name,
                "status": "submitted",
            }}

        except grpc.RpcError as rpc_err:
            details = str(rpc_err.details()) if hasattr(rpc_err, "details") else str(rpc_err)
            if "10008" not in details and "任务已存在" not in details:
                raise

            _append_log(
                task_id,
                "磁力链接已存在 (code 10008)，搜索现有下载...",
                "WARNING",
                step="submit_magnet",
            )

            download_root = config.get("download_root_folder", "/Downloads")
            existing_files = _find_existing_download(cd2, download_root, task_id)

            if existing_files:
                _append_log(task_id, f"找到现有下载: {len(existing_files)} 个文件", step="submit_magnet")
                _update_task(task_id, {
                    "download.status": "found_existing",
                    "download.found_files": len(existing_files),
                })
            else:
                _append_log(task_id, "未找到现有文件，将在等待下载步骤中继续轮询", "WARNING", step="submit_magnet")
                _update_task(task_id, {"download.status": "submitted_duplicate"})

            return {**task, "download": {
                "status": "found_existing" if existing_files else "submitted_duplicate",
                "found_files": len(existing_files),
            }}
    finally:
        cd2.close()


def _is_step_done(task: dict, step: str, config: dict) -> bool:
    client = _build_cd2_client(config)
    gateway = CloudDrive2Gateway(client)
    try:
        if step == "submit_magnet":
            dl = task.get("download", {})
            if dl.get("cd2_task_name") or dl.get("status") in ("submitted", "found_existing"):
                return True
        elif step == "scan_files":
            if task.get("scanned_files"):
                return True
        elif step == "select_videos":
            if task.get("selected_videos"):
                return True
        elif step == "rename_files":
            selected = task.get("selected_videos", [])
            if selected and all(v.get("renamed_path") for v in selected):
                return True
        elif step == "move_files":
            target = task.get("target_path")
            if not target:
                return False
            try:
                files = [_file_to_dict(f) for f in gateway.list_files(target)]
                video_exts = set(config.get("video_extensions", []))
                has_videos = any(
                    PurePosixPath(f["name"]).suffix.lower() in video_exts
                    for f in files
                    if not f.get("is_dir")
                )
                return has_videos
            except Exception:
                return False
        elif step == "verify_result":
            if task.get("verified"):
                return True
        elif step == "cleanup_files":
            if task.get("cleaned"):
                return True
        return False
    finally:
        client.close()
