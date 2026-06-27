"""Storage worker runner — lifecycle management and task execution."""

import logging
import threading
import traceback

from app.modules.storage.config.schemas import StorageConfig
from app.modules.storage.worker.context import StorageTaskContext, StorageTaskLogger
from app.modules.storage.worker.scheduler import StorageTaskScheduler
from app.modules.storage.worker.state_machine import StorageStateMachine
from shared.integrations.storage_providers.clouddrive2.gateway import CloudDrive2Gateway

logger = logging.getLogger("storage_worker")

POLL_INTERVAL_SECONDS = 30


class StorageWorker:
    def __init__(
        self,
        task_repository,
        movie_repository,
        magnet_repository,
        config_repository,
        provider_factory,
        state_machine: StorageStateMachine,
    ) -> None:
        self.task_repository = task_repository
        self.movie_repository = movie_repository
        self.magnet_repository = magnet_repository
        self.config_repository = config_repository
        self.provider_factory = provider_factory
        self.state_machine = state_machine
        self.scheduler = StorageTaskScheduler(task_repository)
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.current_task_id: str | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.run_forever, daemon=True, name="storage-worker")
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5.0)

    def run_forever(self) -> None:
        logger.info("Storage worker started")
        while not self.stop_event.is_set():
            self.execute_next_task()
            self.stop_event.wait(timeout=POLL_INTERVAL_SECONDS)
        logger.info("Storage worker stopped")

    def execute_next_task(self) -> None:
        task = self.scheduler.fetch_next_task()
        if task is None:
            return

        self.current_task_id = task["task_id"]
        try:
            config = StorageConfig().model_dump()
            config.update(self.config_repository.get_default())
            client = self.provider_factory.create(config)
            try:
                context = StorageTaskContext(
                    task=task,
                    config=config,
                    task_repository=self.task_repository,
                    movie_repository=self.movie_repository,
                    magnet_repository=self.magnet_repository,
                    provider=CloudDrive2Gateway(client),
                    logger=StorageTaskLogger(task["task_id"]),
                )
                self.state_machine.execute(context)
            finally:
                close = getattr(client, "close", None)
                if callable(close):
                    close()
        except Exception as exc:
            logger.error("Storage worker error: %s\n%s", exc, traceback.format_exc())
            self.task_repository.mark_failed(
                task["task_id"],
                task.get("step") or "unknown",
                {"message": str(exc), "type": exc.__class__.__name__},
                retryable=False,
            )
        finally:
            self.current_task_id = None
