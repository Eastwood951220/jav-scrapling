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
