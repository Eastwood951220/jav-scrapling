from scraper.config.settings import REQUEST_TIMEOUT, USE_DYNAMIC_FETCHER
from scraper.config.sites import JAVDB_SITE
from scraper.cookies.cookie_manager import CookieManager
from scraper.fetchers.scrapling_fetcher import ScraplingFetcher
from scraper.pipelines.movie_pipeline import MoviePipeline
from scraper.spiders.javdb.javdb_constants import (
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
    TASK_STATUS_SKIPPED,
)
from scraper.spiders.javdb.javdb_spider import JavdbSpider
from scraper.tasks.task_schema import CrawlTask


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

    def crawl_javdb_task(self, task: CrawlTask, stop_check=None) -> dict:
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
                "items": [],
                "reason": "skipped_by_config",
            }

        spider = self._build_spider()
        pipeline = MoviePipeline()
        collected_items: list[dict] = []

        def collect_completed_detail(detail_task: dict) -> None:
            item = self._build_detail_item(task, detail_task)
            if not item:
                return

            cleaned = pipeline.process_item(item)
            if cleaned is not None:
                collected_items.append(cleaned)
                print(
                    f"[Task:{task.name}][Collect] "
                    f"code={cleaned.get('code')} collection={cleaned.get('config_task_name')}"
                )
            else:
                print(
                    f"[Task:{task.name}][Collect] skipped invalid "
                    f"code={item.get('code')} url={item.get('source_url')}"
                )

        detail_tasks = spider.run_task(
            task,
            on_detail_completed=collect_completed_detail,
            stop_check=stop_check,
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
            "saved": 0,
            "items": collected_items,
            "stopped": stop_check is not None and stop_check(),
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

    def crawl_javdb_tasks(self, tasks: list[CrawlTask], stop_check=None) -> dict:
        results = []
        total_config_tasks = len(tasks)

        print(f"[Tasks] start total_config_tasks={total_config_tasks}")

        for index, task in enumerate(tasks, start=1):
            if stop_check and stop_check():
                print(f"[Tasks] {index}/{total_config_tasks} stopped by signal")
                break

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
                    "items": [],
                    "reason": "skipped_by_config",
                }
                results.append(result)
                continue

            result = self.crawl_javdb_task(task, stop_check=stop_check)
            results.append(result)

            if result.get("stopped"):
                print(f"[Tasks] {index}/{total_config_tasks} stopped after task={task.name}")
                break

        all_items = []
        for r in results:
            all_items.extend(r.get("items", []))

        summary = {
            "total_config_tasks": total_config_tasks,
            "executed_config_tasks": sum(1 for item in results if not item.get("is_skip")),
            "skipped_config_tasks": sum(1 for item in results if item.get("is_skip")),
            "total_detail_tasks": sum(item.get("total_tasks", 0) for item in results),
            "completed_detail_tasks": sum(item.get("completed_tasks", 0) for item in results),
            "failed_detail_tasks": sum(item.get("failed_tasks", 0) for item in results),
            "skipped_detail_tasks": sum(item.get("skipped_tasks", 0) for item in results),
            "saved": 0,
            "items": all_items,
            "results": results,
        }

        print(f"[Tasks] all finished summary={summary}")

        return summary
