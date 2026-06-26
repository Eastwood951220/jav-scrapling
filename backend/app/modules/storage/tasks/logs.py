import json
from pathlib import Path
from typing import Any

from scraper.config.settings import RUN_DATA_DIR


def storage_task_log_path(task_id: str) -> Path:
    """Return storage task log path: run_data/storage_tasks/{task_id}.jsonl."""
    return RUN_DATA_DIR / "storage_tasks" / f"{task_id}.jsonl"


def append_storage_task_log(task_id: str, entry: dict[str, Any]) -> None:
    path = storage_task_log_path(task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def load_storage_task_logs(task_id: str) -> list[dict[str, Any]]:
    path = storage_task_log_path(task_id)
    if not path.exists():
        return []

    entries: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def delete_storage_task_logs(task_id: str) -> bool:
    path = storage_task_log_path(task_id)
    if not path.exists():
        return False
    path.unlink()
    return True
