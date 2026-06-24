from config.settings import REQUEST_TIMEOUT, USE_DYNAMIC_FETCHER
from config.sites import JAVDB_SITE
from cookies.cookie_manager import CookieManager
from database.repositories.movie_repository import MovieRepository
from fetchers.scrapling_fetcher import ScraplingFetcher
from pipelines.movie_pipeline import MoviePipeline
from spiders.javdb.javdb_constants import (
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
    TASK_STATUS_SKIPPED,
)
from spiders.javdb.javdb_spider import JavdbSpider
from tasks.task_schema import CrawlTask


class MovieService:
    def _build_spider(self) -> JavdbSpider:
        cookie_manager = CookieManager(JAVDB_SITE["cookie_file"])
        cookies = cookie_manager.load()

        fetcher = ScraplingFetcher(
            headers=JAVDB_SITE["headers"],
            cookies=cookies,
            timeout=REQUEST_TIMEOUT,
            dynamic=USE_DYNAMIC_FETCHER,
        )

        return JavdbSpider(fetcher=fetcher)

    def _build_pipeline(self) -> MoviePipeline:
        repository = MovieRepository()
        return MoviePipeline(repository=repository)

    def crawl_javdb_task(self, task: CrawlTask) -> dict:
        if task.is_skip:
            return {
                "task_name": task.name,
                "source": task.source,
                "url": task.url,
                "final_url": task.final_url,
                "is_skip": True,
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "skipped_tasks": 0,
                "saved": 0,
                "reason": "skipped_by_config",
            }

        spider = self._build_spider()
        pipeline = self._build_pipeline()
        saved_count = 0

        def save_completed_detail(detail_task: dict) -> None:
            nonlocal saved_count

            item = self._build_detail_item(task, detail_task)
            if not item:
                return

            if pipeline.process_item(item):
                saved_count += 1
                print(
                    f"[Task:{task.name}][DB] saved "
                    f"code={item.get('code')} collection={item.get('config_task_name')}"
                )
            else:
                print(
                    f"[Task:{task.name}][DB] skipped save "
                    f"code={item.get('code')} url={item.get('source_url')}"
                )

        detail_tasks = spider.run_task(
            task,
            on_detail_completed=save_completed_detail,
        )

        completed_tasks = [
            item for item in detail_tasks if item.get("status") == TASK_STATUS_COMPLETED
        ]

        failed_count = sum(
            1 for item in detail_tasks if item.get("status") == TASK_STATUS_FAILED
        )
        skipped_count = sum(
            1 for item in detail_tasks if item.get("status") == TASK_STATUS_SKIPPED
        )

        return {
            "task_name": task.name,
            "source": task.source,
            "url": task.url,
            "final_url": task.final_url,
            "is_skip": task.is_skip,
            "total_tasks": len(detail_tasks),
            "completed_tasks": len(completed_tasks),
            "failed_tasks": failed_count,
            "skipped_tasks": skipped_count,
            "saved": saved_count,
        }

    def _build_detail_item(self, task: CrawlTask, detail_task: dict) -> dict:
        detail = detail_task.get("detail") or {}
        if not detail:
            return {}

        source_code = detail_task.get("code")

        return {
            **detail,
            "code": detail.get("code") or source_code,
            "name": task.name,
            "source_url": detail_task.get("url"),
            "source_name": detail_task.get("name"),
            "source_code": source_code,
            "source_page": detail_task.get("source_page"),
            "parent_task_name": detail_task.get("parent_task_name"),
            "config_task_name": task.name,
        }

    def crawl_javdb_tasks(self, tasks: list[CrawlTask]) -> dict:
        results = []
        total_config_tasks = len(tasks)

        print(f"[Tasks] start total_config_tasks={total_config_tasks}")

        for index, task in enumerate(tasks, start=1):
            print(
                f"[Tasks] {index}/{total_config_tasks} "
                f"name={task.name} skip={task.is_skip} url={task.url}"
            )

            if task.is_skip:
                result = {
                    "task_name": task.name,
                    "source": task.source,
                    "url": task.url,
                    "final_url": task.final_url,
                    "is_skip": True,
                    "total_tasks": 0,
                    "completed_tasks": 0,
                    "failed_tasks": 0,
                    "skipped_tasks": 0,
                    "saved": 0,
                    "reason": "skipped_by_config",
                }
                results.append(result)
                print(f"[Tasks] {index}/{total_config_tasks} skipped by config name={task.name}")
                continue

            result = self.crawl_javdb_task(task)
            results.append(result)

            print(f"[Tasks] {index}/{total_config_tasks} finished result={result}")

        summary = {
            "total_config_tasks": total_config_tasks,
            "executed_config_tasks": sum(1 for item in results if not item.get("is_skip")),
            "skipped_config_tasks": sum(1 for item in results if item.get("is_skip")),
            "total_detail_tasks": sum(item.get("total_tasks", 0) for item in results),
            "completed_detail_tasks": sum(item.get("completed_tasks", 0) for item in results),
            "failed_detail_tasks": sum(item.get("failed_tasks", 0) for item in results),
            "skipped_detail_tasks": sum(item.get("skipped_tasks", 0) for item in results),
            "saved": sum(item.get("saved", 0) for item in results),
            "results": results,
        }

        print(f"[Tasks] all finished summary={summary}")

        return summary
