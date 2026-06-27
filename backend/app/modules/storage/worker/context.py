"""Worker context — shared state and logger passed to each pipeline step."""

from dataclasses import dataclass

from app.modules.storage.tasks.logs import append_storage_task_log
from shared.common.datetime import utc_now


class StorageTaskLogger:
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id

    def log(self, message: str, level: str = "INFO", step: str | None = None) -> None:
        append_storage_task_log(
            self.task_id,
            {
                "timestamp": utc_now().isoformat(),
                "level": level,
                "step": step,
                "message": message,
            },
        )


@dataclass
class StorageTaskContext:
    task: dict
    config: dict
    task_repository: object
    movie_repository: object
    magnet_repository: object
    provider: object
    logger: StorageTaskLogger
