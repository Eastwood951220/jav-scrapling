from config.logging import get_logger
from services.movie_service import MovieService
from tasks.task_loader import TaskLoader


class TaskManager:
    def __init__(self):
        self.logger = get_logger("TaskManager")
        self.task_loader = TaskLoader()
        self.movie_service = MovieService()

    def run_from_config(self) -> dict | None:
        tasks = self.task_loader.load_tasks()

        if not tasks:
            self.logger.warning("没有可执行任务")
            return None

        result = self.movie_service.crawl_javdb_tasks(tasks)

        self.logger.info("任务执行完成: %s", result)
        print(f"[TaskManager] finished result={result}")

        return result
