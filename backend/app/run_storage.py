"""File-based storage for run logs.

Stores per-run logs as JSONL files under RUN_DATA_DIR to avoid bloating
MongoDB documents with unbounded log arrays.

Result data is stored in MongoDB only (not in files).
"""

import json
import shutil
from pathlib import Path
from typing import Any

from scraper.config.settings import RUN_DATA_DIR


def _log_path(run_id: str) -> Path:
    """Return path: RUN_DATA_DIR/{run_id}.jsonl"""
    return RUN_DATA_DIR / f"{run_id}.jsonl"


def _legacy_log_jsonl_path(run_id: str) -> Path:
    """Return legacy path: RUN_DATA_DIR/{run_id}/logs.jsonl"""
    return RUN_DATA_DIR / run_id / "logs.jsonl"


def _legacy_log_json_path(run_id: str) -> Path:
    """Return legacy path: RUN_DATA_DIR/{run_id}/logs.json"""
    return RUN_DATA_DIR / run_id / "logs.json"


def save_logs(run_id: str, logs: list[dict[str, Any]]) -> None:
    """Write logs array to RUN_DATA_DIR/{run_id}.jsonl (one JSON object per line)."""
    path = _log_path(run_id)
    RUN_DATA_DIR.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(entry, ensure_ascii=False, default=str) + "\n" for entry in logs]
    path.write_text("".join(lines), encoding="utf-8")


def load_logs(run_id: str) -> list[dict[str, Any]]:
    """Read logs from file. Returns empty list if file does not exist."""
    return load_logs_jsonl(run_id)


def append_log_jsonl(run_id: str, entry: dict[str, Any]) -> None:
    """Append a single log entry as a JSON line to RUN_DATA_DIR/{run_id}.jsonl."""
    path = _log_path(run_id)
    RUN_DATA_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


def load_logs_jsonl(run_id: str) -> list[dict[str, Any]]:
    """Read logs from JSONL file. Falls back to legacy subfolder paths."""
    # 优先: 新扁平路径
    path = _log_path(run_id)
    if path.exists():
        entries = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    # 回退: 旧 JSONL 路径
    legacy_jsonl = _legacy_log_jsonl_path(run_id)
    if legacy_jsonl.exists():
        entries = []
        with open(legacy_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    # 回退: 旧 JSON 数组路径
    legacy_json = _legacy_log_json_path(run_id)
    if legacy_json.exists():
        return json.loads(legacy_json.read_text(encoding="utf-8"))

    return []


def get_result_summary(result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a copy of result with the 'items' key removed.

    This lightweight summary is stored in MongoDB for list-view display.
    """
    if result is None:
        return None
    return {k: v for k, v in result.items() if k != "items"}


def delete_run_dir(run_id: str) -> bool:
    """Delete the run's data files (flat + legacy). Returns True if any deleted."""
    deleted = False

    # 删除新扁平文件
    path = _log_path(run_id)
    if path.exists():
        path.unlink()
        deleted = True

    # 清理旧子文件夹（如果存在）
    legacy_dir = RUN_DATA_DIR / run_id
    if legacy_dir.exists() and legacy_dir.is_dir():
        shutil.rmtree(legacy_dir)
        deleted = True

    return deleted
