"""Storage worker — single-process sequential executor for storage tasks.

Processes tasks from the ``storage_tasks`` MongoDB collection through a
multi-step pipeline: prepare → submit_magnet → waiting_download → scan_files
→ select_videos → rename_files → move_files → verify_result → cleanup_files.

Priority scheduling ensures recovery tasks and completed downloads are
processed before new pending tasks.
"""

import logging
import os
import random
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import PurePosixPath

from app.db.collections import MOVIES, STORAGE_CONFIG, STORAGE_TASKS
from app.modules.storage.tasks.logs import append_storage_task_log
from clouddrive.clouddrive_grpc_client import CloudDriveGrpcClient

# ---------------------------------------------------------------------------
# Module-level shared state (matches task_queue.py pattern)
# ---------------------------------------------------------------------------

_stop_event = threading.Event()
_worker_running = False
_worker_lock = threading.Lock()
_current_task_id: str | None = None
_current_step: str | None = None

TASKS_COLLECTION = STORAGE_TASKS
MOVIES_COLLECTION = MOVIES
CONFIG_COLLECTION = STORAGE_CONFIG
CONFIG_KEY = {"_key": "default"}

PIPELINE_STEPS = [
    "prepare",
    "submit_magnet",
    "waiting_download",
    "scan_files",
    "select_videos",
    "rename_files",
    "move_files",
    "verify_result",
    "cleanup_files",
]

POLL_INTERVAL_SECONDS = 30  # how often the worker checks for new tasks

logger = logging.getLogger("storage_worker")


def _append_log(task_id: str, message: str, level: str = "INFO", step: str | None = None) -> None:
    """Append a log entry to the task's JSONL log file."""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "step": step or _current_step,
        "message": message,
    }
    try:
        append_storage_task_log(task_id, log_entry)
    except Exception as e:
        print(
            f"[ERROR] Failed to append storage log: {e} "
            f"(task_id={task_id}, msg={message[:100]})",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# MongoDB helpers
# ---------------------------------------------------------------------------

def _tasks_col():
    from scraper.database.mongo_client import get_mongo_db
    return get_mongo_db()[TASKS_COLLECTION]


def _movies_col():
    from scraper.database.mongo_client import get_mongo_db
    return get_mongo_db()[MOVIES_COLLECTION]


def _config_col():
    from scraper.database.mongo_client import get_mongo_db
    return get_mongo_db()[CONFIG_COLLECTION]


def _load_storage_config() -> dict:
    """Load the default storage config from MongoDB, falling back to defaults."""
    from app.modules.storage.config.schemas import StorageConfig

    doc = _config_col().find_one(CONFIG_KEY)
    if not doc:
        return StorageConfig().model_dump()

    doc.pop("_id", None)
    doc.pop("_key", None)
    doc.pop("updated_at", None)

    defaults = StorageConfig().model_dump()
    merged = {**defaults, **doc}
    return merged


def _update_task(task_id: str, update: dict) -> None:
    """Update a storage task document."""
    update["updated_at"] = datetime.now(timezone.utc)
    _tasks_col().update_one({"task_id": task_id}, {"$set": update})


def _update_movie_summary(movie_id: str, task_id: str, status: str) -> None:
    """Update the movie's storage_summary subdocument."""
    from bson import ObjectId
    from bson.errors import InvalidId

    try:
        oid = ObjectId(movie_id)
    except (InvalidId, TypeError):
        return
    _movies_col().update_one(
        {"_id": oid},
        {"$set": {
            "storage_summary.last_task_id": task_id,
            "storage_summary.last_status": status,
            "storage_summary.updated_at": datetime.now(timezone.utc),
        }},
    )


# ---------------------------------------------------------------------------
# CloudDrive2 client builder
# ---------------------------------------------------------------------------

def _build_cd2_client(config: dict) -> CloudDriveGrpcClient:
    """Build a CloudDriveGrpcClient from storage config."""
    raw_host = config.get("grpc_host", "localhost:9798")
    token = config.get("api_token", "")
    timeout = config.get("request_timeout_seconds", 60)

    host = raw_host
    if host.startswith("http://"):
        host = host[7:]
    elif host.startswith("https://"):
        host = host[8:]
    host = host.rstrip("/")

    return CloudDriveGrpcClient(host=host, token=token, timeout=timeout)


def _file_to_dict(f) -> dict:
    """Convert a gRPC CloudDriveFile to a plain dict."""
    return {
        "name": f.name,
        "path": f.fullPathName if hasattr(f, "fullPathName") else f.name,
        "size": f.size,
        "is_dir": f.isDirectory if hasattr(f, "isDirectory") else False,
    }


def _get_file_info(cd2, path: str) -> dict | None:
    """Get file info via gRPC. Returns dict or None if not found."""
    parent = PurePosixPath(path).parent.as_posix() or "/"
    name = PurePosixPath(path).name
    found = cd2.find_file_by_path(parent, name)
    if found is None:
        return None
    return _file_to_dict(found)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _download_folder(task: dict, config: dict) -> str:
    """Return the CloudDrive2 path for a task's download folder."""
    root = config.get("download_root_folder", "/Downloads")
    if config.get("use_task_subfolder", True):
        return str(PurePosixPath(root) / task["task_id"])
    return root


def _target_folder(task: dict, config: dict) -> str:
    """Return the CloudDrive2 path for a task's target folder.

    Structure: {target_folder}/{source_task_name}/{movie_code}
    When source_task_name is a list, uses the LAST element.
    Falls back to movie_code if no task name is available.
    """
    target = config.get("target_folder", "/Movies")
    task_name = task.get("source_task_name", "")
    movie_code = task["movie_code"]

    # Handle list: use last element
    if isinstance(task_name, list):
        task_name = task_name[-1] if task_name else ""

    if task_name:
        return str(PurePosixPath(target) / task_name / movie_code)
    return str(PurePosixPath(target) / movie_code)


def _all_target_folders(task: dict, config: dict) -> list[str]:
    """Return ALL target folder paths when source_task_name is a list.

    For a single name or empty, returns a list with one element (same as _target_folder).
    """
    target = config.get("target_folder", "/Movies")
    task_name = task.get("source_task_name", "")
    movie_code = task["movie_code"]

    if isinstance(task_name, list) and len(task_name) > 1:
        return [str(PurePosixPath(target) / name / movie_code) for name in task_name]
    # Single name or empty — just one target
    return [_target_folder(task, config)]


def _disc_number(file_name: str) -> int | None:
    """Try to extract a disc/part number from a filename.

    Looks for patterns like CD1, CD2, -cd1, _cd2, Disc1, disc01, etc.
    """
    import re

    match = re.search(r"(?:cd|disc|part)[_\-\s]?(\d+)", file_name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


# ---------------------------------------------------------------------------
# Step idempotent checks
# ---------------------------------------------------------------------------

def _is_step_done(task: dict, step: str, config: dict) -> bool:
    """Check if a step was already completed and can be skipped."""
    cd2 = _build_cd2_client(config)
    try:
        if step == "submit_magnet":
            # Already submitted if task has a cd2_task_name
            if task.get("download", {}).get("cd2_task_name"):
                return True

        elif step == "scan_files":
            # Already scanned if task has scanned_files
            if task.get("scanned_files"):
                return True

        elif step == "select_videos":
            # Already selected if task has selected_videos
            if task.get("selected_videos"):
                return True

        elif step == "rename_files":
            # Already renamed if all selected videos have renamed_path
            selected = task.get("selected_videos", [])
            if selected and all(v.get("renamed_path") for v in selected):
                return True

        elif step == "move_files":
            # Already moved if target files exist
            target = task.get("target_path")
            if not target:
                return False
            try:
                files = [_file_to_dict(f) for f in cd2.list_sub_files(target)]
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
            # Already verified if verified flag is set
            if task.get("verified"):
                return True

        elif step == "cleanup_files":
            # Already cleaned if cleaned flag is set
            if task.get("cleaned"):
                return True

        return False
    finally:
        cd2.close()


def _check_stop(task_id: str) -> bool:
    """Return True if stop was requested for this task."""
    if _stop_event.is_set():
        _append_log(task_id, "收到停止信号", "WARNING")
        return True
    return False


# ---------------------------------------------------------------------------
# Step implementations
# ---------------------------------------------------------------------------

def _step_prepare(task: dict, config: dict) -> dict:
    """Step 1: Prepare — load movie data and validate prerequisites."""
    task_id = task["task_id"]

    # Load movie data
    from bson import ObjectId
    from bson.errors import InvalidId

    try:
        movie_oid = ObjectId(task["movie_id"])
    except (InvalidId, TypeError):
        raise ValueError(f"无效的 movie_id: {task['movie_id']}")

    movie = _movies_col().find_one({"_id": movie_oid})
    if not movie:
        raise ValueError(f"未找到电影: {task['movie_id']}")

    # Validate magnet URL
    magnet_url = task.get("magnet_url") or movie.get("magnet_url", "")
    if not magnet_url:
        raise ValueError("缺少磁力链接")

    # Load task name for target folder structure
    source_task_name = movie.get("source_task_name", "")

    # Compute paths (target includes task name subfolder)
    task_with_name = {**task, "source_task_name": source_task_name}
    download_path = _download_folder(task, config)
    target_path = _target_folder(task_with_name, config)
    target_paths = _all_target_folders(task_with_name, config)

    _update_task(task_id, {
        "download_path": download_path,
        "target_path": target_path,
        "target_paths": target_paths,
        "magnet_url": magnet_url,
        "source_task_name": source_task_name,
    })

    _append_log(task_id, f"准备完成: download={download_path}, target={target_path}, targets={target_paths}")

    return {
        **task_with_name,
        "download_path": download_path,
        "target_path": target_path,
        "target_paths": target_paths,
        "magnet_url": magnet_url,
    }


def _step_submit_magnet(task: dict, config: dict) -> dict:
    """Step 2: Submit magnet to CloudDrive2 offline download."""
    task_id = task["task_id"]
    magnet_url = task["magnet_url"]
    download_path = task["download_path"]

    cd2 = _build_cd2_client(config)
    try:
        # Create download folder
        cd2.create_folder(download_path)

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
    finally:
        cd2.close()


def _step_waiting_download(task: dict, config: dict) -> dict:
    """Step 3: Poll download folder until files appear (gRPC has no task-status API)."""
    task_id = task["task_id"]
    download_path = task.get("download_path", "")

    if not download_path:
        raise ValueError("缺少 download_path，无法查询下载状态")

    poll_min = config.get("download_poll_interval_min", 5.0)
    poll_max = config.get("download_poll_interval_max", 15.0)
    max_wait_min = config.get("download_max_wait_minutes", 120)
    deadline = time.monotonic() + max_wait_min * 60

    cd2 = _build_cd2_client(config)
    poll_count = 0
    try:
        while True:
            if _check_stop(task_id):
                return task

            if time.monotonic() > deadline:
                raise RuntimeError(f"下载超时: 超过 {max_wait_min} 分钟")

            poll_count += 1
            try:
                entries = [_file_to_dict(f) for f in cd2.list_sub_files(download_path)]
                if entries:
                    # CloudDrive2 offline downloads create subdirectories — any content means download exists
                    dir_count = sum(1 for e in entries if e.get("is_dir"))
                    file_count = len(entries) - dir_count
                    total_size = sum(e.get("size", 0) for e in entries)

                    # If there are subdirectories, scan inside them for actual files
                    if dir_count > 0:
                        for d in [e for e in entries if e.get("is_dir")]:
                            try:
                                sub_files = [_file_to_dict(f) for f in cd2.list_sub_files(d["path"])]
                                sub_non_dir = [f for f in sub_files if not f.get("is_dir")]
                                if sub_non_dir:
                                    total_size += sum(f.get("size", 0) for f in sub_non_dir)
                                    file_count += len(sub_non_dir)
                            except Exception:
                                pass

                    _update_task(task_id, {
                        "download.status": "completed",
                        "download.progress": 100,
                        "progress": 100,
                    })
                    _append_log(
                        task_id,
                        f"下载完成: 检测到 {file_count} 个文件, "
                        f"总大小 {total_size / (1024*1024):.1f} MB",
                        step="waiting_download",
                    )
                    return task

                _append_log(
                    task_id,
                    f"轮询 #{poll_count}: 目录为空，等待中...",
                    step="waiting_download",
                )
            except Exception as exc:
                _append_log(
                    task_id,
                    f"轮询 #{poll_count} 异常: {exc}",
                    "WARNING",
                    step="waiting_download",
                )

            # Sleep with stop check
            poll_interval = random.uniform(poll_min, poll_max)
            if _stop_event.wait(timeout=poll_interval):
                _append_log(task_id, "下载轮询期间收到停止信号", "WARNING", step="waiting_download")
                return task
    finally:
        cd2.close()


def _step_scan_files(task: dict, config: dict) -> dict:
    """Step 4: List files in the download folder (recursively for subdirectories)."""
    task_id = task["task_id"]
    download_path = task["download_path"]

    cd2 = _build_cd2_client(config)
    try:
        # Scan recursively — CloudDrive2 offline downloads create subdirectories
        all_entries = [_file_to_dict(f) for f in cd2.list_sub_files(download_path)]
        files = []
        for entry in all_entries:
            if entry.get("is_dir"):
                try:
                    sub_entries = [_file_to_dict(f) for f in cd2.list_sub_files(entry["path"])]
                    files.extend(sub_entries)
                except Exception:
                    files.append(entry)
            else:
                files.append(entry)

        scanned = [
            {
                "name": f["name"],
                "path": f["path"],
                "size": f["size"],
                "is_dir": f["is_dir"],
            }
            for f in files
            if not f.get("is_dir")
        ]

        _update_task(task_id, {"scanned_files": scanned})
        _append_log(task_id, f"扫描到 {len(scanned)} 个文件")

        return {**task, "scanned_files": scanned}
    finally:
        cd2.close()


def _step_select_videos(task: dict, config: dict) -> dict:
    """Step 5: Filter files by extension and size, identify main videos."""
    task_id = task["task_id"]
    scanned = task.get("scanned_files", [])

    video_exts = set(config.get("video_extensions", []))
    min_size = config.get("minimum_video_size_mb", 100) * 1024 * 1024
    exclude_kw = [kw.lower() for kw in config.get("excluded_filename_keywords", [])]

    videos = []
    excluded = []
    subtitles = []
    covers = []
    other = []

    for f in scanned:
        name = f["name"]
        ext = PurePosixPath(name).suffix.lower()
        name_lower = name.lower()

        # Check exclusion keywords
        if any(kw in name_lower for kw in exclude_kw):
            excluded.append(f)
            continue

        # Video files
        if ext in video_exts:
            if f["size"] >= min_size:
                videos.append({**f, "video_type": "main"})
            else:
                excluded.append(f)
            continue

        # Subtitle files
        if ext in (".srt", ".ass", ".ssa", ".sub", ".sup", ".idx"):
            subtitles.append(f)
            continue

        # Cover images
        if ext in (".jpg", ".jpeg", ".png", ".bmp"):
            covers.append(f)
            continue

        other.append(f)

    selected_videos = videos

    _update_task(task_id, {
        "selected_videos": selected_videos,
        "excluded_files": excluded,
        "subtitle_files": subtitles,
        "cover_files": covers,
    })

    _append_log(
        task_id,
        f"文件筛选: videos={len(videos)}, excluded={len(excluded)}, "
        f"subtitles={len(subtitles)}, covers={len(covers)}, other={len(other)}"
    )

    return {
        **task,
        "selected_videos": selected_videos,
        "excluded_files": excluded,
        "subtitle_files": subtitles,
        "cover_files": covers,
    }


def _step_rename_files(task: dict, config: dict) -> dict:
    """Step 6: Rename video files using the configured template."""
    task_id = task["task_id"]
    selected = task.get("selected_videos", [])
    movie_code = task.get("movie_code", "UNKNOWN")

    if not selected:
        _append_log(task_id, "无需重命名，没有选中的视频文件")
        return task

    multi = len(selected) > 1
    single_tpl = config.get("single_filename_template", "{code}{ext}")
    multi_tpl = config.get("multi_filename_template", "{code}{ext}")

    cd2 = _build_cd2_client(config)
    try:
        renamed = []
        for i, video in enumerate(selected):
            if _check_stop(task_id):
                return {**task, "selected_videos": renamed + selected[i:]}

            old_path = video["path"]
            ext = PurePosixPath(video["name"]).suffix

            if multi:
                disc_num = _disc_number(video["name"]) or (i + 1)
                new_name = multi_tpl.replace("{code}", movie_code).replace("{ext}", ext)
                new_name = new_name.replace("{disc}", str(disc_num))
                # If template doesn't have {disc}, append -CD{n}
                if "{disc}" not in multi_tpl:
                    stem = PurePosixPath(new_name).stem
                    new_ext = PurePosixPath(new_name).suffix
                    new_name = f"{stem}-CD{disc_num}{new_ext}"
            else:
                new_name = single_tpl.replace("{code}", movie_code).replace("{ext}", ext)

            new_path = str(PurePosixPath(old_path).parent / new_name)

            try:
                cd2.rename_file(old_path, new_name)
                renamed.append({**video, "renamed_path": new_path, "renamed_name": new_name})
                _append_log(task_id, f"重命名: {video['name']} → {new_name}")
            except Exception as e:
                _append_log(task_id, f"重命名失败: {video['name']}: {e}", "ERROR")
                renamed.append({**video, "rename_error": str(e)})

        _update_task(task_id, {"selected_videos": renamed})
        return {**task, "selected_videos": renamed}
    finally:
        cd2.close()


def _step_move_files(task: dict, config: dict) -> dict:
    """Step 7: Move renamed videos (and optionally subtitles/covers) to target folder."""
    task_id = task["task_id"]
    selected = task.get("selected_videos", [])
    target_path = task["target_path"]

    # Only move video files (not covers/subtitles)
    files_to_move = list(selected)

    if not files_to_move:
        _append_log(task_id, "无需移动，没有文件")
        return task

    cd2 = _build_cd2_client(config)
    try:
        # Ensure target folder exists
        if config.get("auto_create_target_folder", True):
            cd2.create_folder(target_path)

        moved = []
        for i, f in enumerate(files_to_move):
            if _check_stop(task_id):
                return task

            src = f.get("renamed_path") or f["path"]
            dst = str(PurePosixPath(target_path) / PurePosixPath(src).name)

            # Idempotent: skip if target file already exists
            existing = _get_file_info(cd2, dst)
            if existing and existing.get("size", 0) > 0:
                _append_log(task_id, f"跳过已存在: {PurePosixPath(dst).name}")
                moved.append({**f, "moved_path": dst})
                continue

            try:
                cd2.move_file([src], target_path)
                moved.append({**f, "moved_path": dst})
                _append_log(task_id, f"已移动: {PurePosixPath(src).name} → {target_path}")
            except Exception as e:
                _append_log(task_id, f"移动失败: {PurePosixPath(src).name}: {e}", "ERROR")
                raise

        _update_task(task_id, {"moved_files": moved})
        return {**task, "moved_files": moved}
    finally:
        cd2.close()


def _step_verify_result(task: dict, config: dict) -> dict:
    """Step 8: Verify target files exist with correct sizes."""
    task_id = task["task_id"]
    # Use moved_files (has moved_path) instead of selected_videos
    moved_files = task.get("moved_files", [])
    target_path = task["target_path"]

    cd2 = _build_cd2_client(config)
    try:
        all_ok = True
        for video in moved_files:
            moved_path = video.get("moved_path")
            if not moved_path:
                all_ok = False
                _append_log(task_id, f"验证失败: {video.get('name')} 缺少 moved_path", "ERROR")
                continue

            info = _get_file_info(cd2, moved_path)
            if not info:
                all_ok = False
                _append_log(task_id, f"验证失败: 文件不存在 {moved_path}", "ERROR")
                continue

            expected_size = video.get("size", 0)
            actual_size = info.get("size", 0)
            if expected_size > 0 and abs(actual_size - expected_size) > 1024:
                all_ok = False
                _append_log(
                    task_id,
                    f"验证失败: 大小不匹配 {PurePosixPath(moved_path).name} "
                    f"(expected={expected_size}, actual={actual_size})",
                    "ERROR",
                )

        _update_task(task_id, {"verified": all_ok})

        if all_ok:
            _append_log(task_id, "验证通过: 所有文件完整")
        else:
            raise RuntimeError("文件验证失败")

        return {**task, "verified": all_ok}
    finally:
        cd2.close()


def _step_cleanup_files(task: dict, config: dict) -> dict:
    """Step 9: Delete temp download folder and excluded files."""
    task_id = task["task_id"]
    download_path = task.get("download_path")

    cd2 = _build_cd2_client(config)
    try:
        # Delete the entire download subfolder
        if download_path and config.get("use_task_subfolder", True):
            try:
                cd2.delete_file(download_path)
                _append_log(task_id, f"已清理下载目录: {download_path}")
            except Exception as e:
                _append_log(task_id, f"清理下载目录失败 (非致命): {e}", "WARNING")

        _update_task(task_id, {"cleaned": True})
        _append_log(task_id, "清理完成")

        return {**task, "cleaned": True}
    finally:
        cd2.close()


# ---------------------------------------------------------------------------
# Step dispatcher
# ---------------------------------------------------------------------------

_STEP_HANDLERS = {
    "prepare": _step_prepare,
    "submit_magnet": _step_submit_magnet,
    "waiting_download": _step_waiting_download,
    "scan_files": _step_scan_files,
    "select_videos": _step_select_videos,
    "rename_files": _step_rename_files,
    "move_files": _step_move_files,
    "verify_result": _step_verify_result,
    "cleanup_files": _step_cleanup_files,
}


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------

def _handle_step_failure(task: dict, step: str, error: Exception, config: dict) -> None:
    """Handle a failed step: retry or mark as retryable/failed."""
    task_id = task["task_id"]
    step_attempt = task.get("step_attempt", 0) + 1
    max_retries = config.get("max_step_retries", 3)
    retry_min = config.get("retry_delay_min", 10.0)
    retry_max = config.get("retry_delay_max", 30.0)

    _append_log(task_id, f"步骤 {step} 失败 (attempt {step_attempt}): {error}", "ERROR")

    if step_attempt < max_retries:
        next_retry = datetime.now(timezone.utc).replace(
            second=0, microsecond=0
        )
        delay_seconds = random.uniform(retry_min, retry_max)
        from datetime import timedelta
        next_retry = next_retry + timedelta(seconds=delay_seconds)

        _update_task(task_id, {
            "status": "waiting_retry",
            "step": step,
            "step_attempt": step_attempt,
            "retry_count": task.get("retry_count", 0) + 1,
            "error_message": str(error),
            "retry.next_retry_at": next_retry,
        })
        _append_log(task_id, f"将在 {delay_seconds:.0f}s 后重试步骤 {step}")
    else:
        _update_task(task_id, {
            "status": "retryable",
            "step": step,
            "step_attempt": step_attempt,
            "retry_count": task.get("retry_count", 0) + 1,
            "error_message": str(error),
        })
        _append_log(task_id, f"步骤 {step} 达到最大重试次数，标记为 retryable")
        _update_movie_summary(task["movie_id"], task_id, "retryable")


# ---------------------------------------------------------------------------
# Task execution
# ---------------------------------------------------------------------------

def _execute_task(task: dict, config: dict) -> None:
    """Execute a single task through the full pipeline."""
    task_id = task["task_id"]
    step = task.get("step") or "prepare"

    # Determine starting step index
    try:
        step_index = PIPELINE_STEPS.index(step)
    except ValueError:
        step_index = 0

    _update_task(task_id, {
        "status": "running",
        "step": step,
        "error_message": None,
    })
    _update_movie_summary(task["movie_id"], task_id, "running")

    _append_log(task_id, f"开始执行 (从步骤 {step})")

    for i in range(step_index, len(PIPELINE_STEPS)):
        current_step = PIPELINE_STEPS[i]

        if _check_stop(task_id):
            _update_task(task_id, {"status": "stopped", "step": current_step})
            _update_movie_summary(task["movie_id"], task_id, "stopped")
            _append_log(task_id, f"任务在步骤 {current_step} 被停止")
            return

        _update_task(task_id, {"step": current_step, "progress": i / len(PIPELINE_STEPS)})
        _current_step = current_step

        # Idempotent check: skip if step already done
        if _is_step_done(task, current_step, config):
            _append_log(task_id, f"步骤 {current_step} 已完成，跳过", step=current_step)
            continue

        handler = _STEP_HANDLERS.get(current_step)
        if not handler:
            _append_log(task_id, f"未知步骤: {current_step}", "ERROR", step=current_step)
            continue

        try:
            _append_log(task_id, f"执行步骤: {current_step}", step=current_step)
            task = handler(task, config)
        except Exception as e:
            _handle_step_failure(task, current_step, e, config)
            return

    # All steps completed
    _update_task(task_id, {
        "status": "completed",
        "step": None,
        "progress": 1.0,
        "error_message": None,
        "completed_at": datetime.now(timezone.utc),
    })
    _update_movie_summary(task["movie_id"], task_id, "completed")
    _append_log(task_id, "任务全部完成")


# ---------------------------------------------------------------------------
# Priority scheduling
# ---------------------------------------------------------------------------

def _fetch_next_task() -> dict | None:
    """Fetch the highest-priority pending task from MongoDB.

    Priority order:
    1. Recovery: status=running (interrupted during previous run)
    2. Retry ready: status=waiting_retry AND retry.next_retry_at <= now
    3. Download complete: status=waiting_download AND download.progress >= 100
    4. New pending: status=pending
    5. Poll ready: status=waiting_download AND download.next_poll_at <= now
    """
    now = datetime.now(timezone.utc)

    # 1. Recovery — tasks left in running state from a crash
    task = _tasks_col().find_one_and_update(
        {"status": "running"},
        {"$set": {"status": "running", "updated_at": now}},
        sort=[("created_at", 1)],
    )
    if task:
        return task

    # 2. Retry ready
    task = _tasks_col().find_one_and_update(
        {"status": "waiting_retry", "retry.next_retry_at": {"$lte": now}},
        {"$set": {"status": "running", "updated_at": now}},
        sort=[("retry.next_retry_at", 1)],
    )
    if task:
        return task

    # 3. Download complete (progress 100 but still in waiting_download)
    task = _tasks_col().find_one_and_update(
        {"status": "waiting_download", "progress": {"$gte": 100}},
        {"$set": {"status": "running", "updated_at": now}},
        sort=[("created_at", 1)],
    )
    if task:
        return task

    # 4. New pending tasks
    task = _tasks_col().find_one_and_update(
        {"status": "pending"},
        {"$set": {"status": "running", "updated_at": now}},
        sort=[("created_at", 1)],
    )
    if task:
        return task

    # 5. Download poll ready
    task = _tasks_col().find_one_and_update(
        {
            "status": "waiting_download",
            "$or": [
                {"download.next_poll_at": {"$lte": now}},
                {"download.next_poll_at": {"$exists": False}},
            ],
        },
        {"$set": {"status": "running", "updated_at": now}},
        sort=[("created_at", 1)],
    )
    if task:
        return task

    return None


# ---------------------------------------------------------------------------
# Worker loop
# ---------------------------------------------------------------------------

def _worker_loop() -> None:
    """Main worker loop. Runs forever until stop_storage_worker() is called."""
    global _current_task_id, _current_step

    logger.info("Storage worker started")

    while not _stop_event.is_set():
        try:
            task = _fetch_next_task()

            if task is None:
                # No tasks available — wait before polling again
                _stop_event.wait(timeout=POLL_INTERVAL_SECONDS)
                continue

            task_id = task["task_id"]
            _current_task_id = task_id
            _current_step = task.get("step")

            config = _load_storage_config()
            _execute_task(task, config)

        except Exception as e:
            tb = traceback.format_exc()
            logger.error("Storage worker error: %s\n%s", e, tb)
            if _current_task_id:
                _append_log(_current_task_id, f"Worker error: {e}", "ERROR")
                _append_log(_current_task_id, tb, "ERROR")
                try:
                    _update_task(_current_task_id, {
                        "status": "failed",
                        "error_message": str(e),
                    })
                except Exception:
                    pass
        finally:
            _current_task_id = None
            _current_step = None

    logger.info("Storage worker stopped")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_storage_worker() -> None:
    """Start the storage worker thread if not already running."""
    global _worker_running

    with _worker_lock:
        if _worker_running:
            logger.info("Storage worker already running")
            return
        _worker_running = True
        _stop_event.clear()

    thread = threading.Thread(target=_worker_loop, daemon=True, name="storage-worker")
    thread.start()
    logger.info("Storage worker thread started")


def stop_storage_worker() -> None:
    """Signal the worker to stop. Blocks briefly for graceful shutdown."""
    global _worker_running

    logger.info("Stopping storage worker...")
    _stop_event.set()

    # Wait briefly for the worker to notice the stop signal
    deadline = time.monotonic() + 5.0
    while _worker_running and time.monotonic() < deadline:
        time.sleep(0.1)

    with _worker_lock:
        _worker_running = False

    logger.info("Storage worker stopped")


def get_worker_status() -> dict:
    """Return current worker status."""
    return {
        "is_running": _worker_running,
        "current_task_id": _current_task_id,
        "current_step": _current_step,
        "stop_requested": _stop_event.is_set(),
    }
