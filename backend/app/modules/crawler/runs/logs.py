import json
from pathlib import Path
from typing import Any

from scraper.config.settings import RUN_DATA_DIR


def run_log_path(run_id: str) -> Path:
    """Return run log path: run_data/runs/{run_id}.jsonl."""
    return RUN_DATA_DIR / "runs" / f"{run_id}.jsonl"


def append_run_log(run_id: str, entry: dict[str, Any]) -> None:
    path = run_log_path(run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def load_run_logs(run_id: str) -> list[dict[str, Any]]:
    path = run_log_path(run_id)
    if not path.exists():
        return []

    entries: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def delete_run_logs(run_id: str) -> bool:
    path = run_log_path(run_id)
    if not path.exists():
        return False
    path.unlink()
    return True
