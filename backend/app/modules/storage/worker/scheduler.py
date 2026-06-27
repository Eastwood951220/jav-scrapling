"""Storage task scheduler — priority-based task selection from the repository."""

from shared.common.datetime import utc_now


class StorageTaskScheduler:
    def __init__(self, task_repository) -> None:
        self.task_repository = task_repository

    def fetch_next_task(self) -> dict | None:
        """Fetch the highest-priority pending task.

        Priority order:
        1. Recovery: status=running (interrupted during previous run)
        2. Retry ready: status=waiting_retry AND retry.next_retry_at <= now
        3. Download poll: status=waiting_download with pending poll
        4. New pending: status=pending
        """
        now = utc_now()
        return (
            self.task_repository.find_next_executable(now)
            or self.task_repository.find_waiting_retry(now)
            or self.task_repository.find_waiting_download(now)
            or self.task_repository.find_pending(now)
        )
