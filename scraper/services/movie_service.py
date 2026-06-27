from scraper.config.settings import REQUEST_TIMEOUT
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
        )

        return JavdbSpider(fetcher=fetcher)

    def crawl_javdb_task(self, task: CrawlTask, stop_check=None, log_callback=None, on_item_saved=None, on_tasks_batch_created=None, on_detail_failed=None, db_check_callback=None, on_detail_check_callback=None) -> dict:
        if task.is_skip:
            if log_callback:
                log_callback(f"跳过任务: {task.name}", "INFO")
            first_url = task.urls[0] if task.urls else None
            return {
                "task_name": task.name,
                "source": first_url.source if first_url else None,
                "url": first_url.url if first_url else None,
                "final_url": first_url.final_url if first_url else None,
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

            cleaned = pipeline.process_item(item, task_name=task.name)
            if cleaned is not None:
                collected_items.append(cleaned)
                msg = (
                    f"[{task.name}] 详情完成: code={cleaned.get('code')} "
                    f"source_task_name={cleaned.get('source_task_name')}"
                )
                print(msg)
                if log_callback:
                    log_callback(msg, "INFO")
                # Per-item save callback
                if on_item_saved:
                    on_item_saved(detail_task, cleaned)
            else:
                msg = f"[{task.name}] 跳过无效数据: code={item.get('code')}"
                print(msg)
                if log_callback:
                    log_callback(msg, "WARNING")

        detail_tasks = spider.run_task(
            task,
            on_detail_completed=collect_completed_detail,
            on_tasks_batch_created=on_tasks_batch_created,
            on_detail_failed=on_detail_failed,
            stop_check=stop_check,
            log_callback=log_callback,
            db_check_callback=db_check_callback,
            on_detail_check_callback=on_detail_check_callback,
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

        # 检测停止: 判断 stop_check 是否被触发
        stopped = stop_check() if stop_check else False

        first_url = task.urls[0] if task.urls else None
        return {
            "task_name": task.name,
            "source": first_url.source if first_url else None,
            "url": first_url.url if first_url else None,
            "final_url": first_url.final_url if first_url else None,
            "is_skip": task.is_skip,
            "total_tasks": len(detail_tasks),
            "completed_tasks": len(completed_tasks),
            "failed_tasks": failed_count,
            "skipped_tasks": skipped_count,
            "saved": 0,  # persistence handled by backend layer
            "items": collected_items,
            "stopped": stopped,
        }

    def _build_detail_item(self, task: CrawlTask, detail_task: dict) -> dict:
        detail = detail_task.get("detail") or {}
        if not detail:
            return {}

        source_code = detail_task.get("code")

        return {
            **detail,
            "code": detail.get("code") or source_code,
            "source_url": detail_task.get("url"),
            "source_name": detail_task.get("name") or detail.get("source_name"),
            "source_code": source_code,
        }

    def crawl_javdb_tasks(self, tasks: list[CrawlTask], stop_check=None) -> dict:
        results = []
        total_config_tasks = len(tasks)

        print(f"[Tasks] start total_config_tasks={total_config_tasks}")

        for index, task in enumerate(tasks, start=1):
            if stop_check and stop_check():
                print(f"[Tasks] {index}/{total_config_tasks} stopped by signal")
                break

            first_url = task.urls[0] if task.urls else None
            print(
                f"[Tasks] {index}/{total_config_tasks} "
                f"name={task.name} skip={task.is_skip} url={first_url.url if first_url else None}"
            )

            if task.is_skip:
                result = {
                    "task_name": task.name,
                    "source": first_url.source if first_url else None,
                    "url": first_url.url if first_url else None,
                    "final_url": first_url.final_url if first_url else None,
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
