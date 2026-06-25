"""File-based storage for run logs and results.

Stores per-run data as JSON files under RUN_DATA_DIR to avoid bloating
MongoDB documents with unbounded logs and result.items arrays.
"""

import json
from pathlib import Path
from typing import Any

from scraper.config.settings import RUN_DATA_DIR


def _run_dir(run_id: str) -> Path:
    """Return the directory for a given run's data files."""
    return RUN_DATA_DIR / run_id


def save_logs(run_id: str, logs: list[dict[str, Any]]) -> None:
    """Write logs array to {RUN_DATA_DIR}/{run_id}/logs.json."""
    path = _run_dir(run_id) / "logs.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(logs, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def load_logs(run_id: str) -> list[dict[str, Any]]:
    """Read logs from file. Returns empty list if file does not exist."""
    path = _run_dir(run_id) / "logs.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def append_log_jsonl(run_id: str, entry: dict[str, Any]) -> None:
    """Append a single log entry as a JSON line to {RUN_DATA_DIR}/{run_id}/logs.jsonl."""
    import json as _json

    path = _run_dir(run_id) / "logs.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    line = _json.dumps(entry, ensure_ascii=False, default=str) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


def load_logs_jsonl(run_id: str) -> list[dict[str, Any]]:
    """Read logs from JSONL file. Falls back to JSON array format for old runs."""
    import json as _json

    jsonl_path = _run_dir(run_id) / "logs.jsonl"
    if jsonl_path.exists():
        entries = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(_json.loads(line))
        return entries

    # Fallback: old JSON array format
    json_path = _run_dir(run_id) / "logs.json"
    if json_path.exists():
        return _json.loads(json_path.read_text(encoding="utf-8"))

    return []


def save_result(run_id: str, result: dict[str, Any]) -> None:
    """Write result dict to {RUN_DATA_DIR}/{run_id}/result.json."""
    path = _run_dir(run_id) / "result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def load_result(run_id: str) -> dict[str, Any] | None:
    """Read result from file. Returns None if file does not exist."""
    path = _run_dir(run_id) / "result.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def get_result_summary(result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a copy of result with the 'items' key removed.

    This lightweight summary is stored in MongoDB for list-view display.
    """
    if result is None:
        return None
    return {k: v for k, v in result.items() if k != "items"}


def delete_run_dir(run_id: str) -> bool:
    """Delete the run's data directory. Returns True if deleted."""
    import shutil

    run_path = _run_dir(run_id)
    if run_path.exists():
        shutil.rmtree(run_path)
        return True
    return False
