from scraper.config.logging import get_logger
from scraper.config.settings import (
    DETAIL_PAGE_DELAY_MAX,
    DETAIL_PAGE_DELAY_MIN,
    LIST_PAGE_DELAY_MAX,
    LIST_PAGE_DELAY_MIN,
    MAX_LIST_PAGES,
    SECURITY_WAIT_SECONDS,
)
from scraper.core.security import is_security_check_page
from scraper.core.throttle import fixed_sleep, random_sleep
from scraper.spiders.base_spider import BaseSpider
from scraper.spiders.javdb.javdb_constants import (
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
    TASK_STATUS_PENDING,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SKIPPED,
)
from scraper.spiders.javdb.javdb_parser import parse_detail_page, parse_search_page
from scraper.spiders.javdb.javdb_urls import build_task_page_url
from scraper.tasks.task_schema import CrawlTask


class JavdbSpider(BaseSpider):
    name = "javdb"

    def __init__(self, fetcher):
        super().__init__(fetcher)
        self.logger = get_logger(self.name)

    def collect_detail_tasks(self, task: CrawlTask) -> list[dict]:
        max_pages = min(task.max_list_pages, MAX_LIST_PAGES)
        detail_tasks: list[dict] = []
        verification_count = 0

        print(
            f"[Task:{task.name}][List] start collect "
            f"url={task.final_url}, max_pages={max_pages}"
        )

        page_no = 1

        while page_no <= max_pages:
            page_url = build_task_page_url(task.final_url or task.url, page_no)
            print(f"[Task:{task.name}][List] fetching page {page_no}/{max_pages}: {page_url}")
            self.logger.info("List page: %s", page_url)

            page = self.fetch(page_url)

            if is_security_check_page(page):
                verification_count += 1
                print(
                    f"[Task:{task.name}][Security] list page {page_no} triggered verification, "
                    f"wait {SECURITY_WAIT_SECONDS}s and retry same page"
                )
                if verification_count >= 5:
                    print(
                        f"[Task:{task.name}][Security] continuous verification count={verification_count}, "
                        "please manually refresh cookies or complete browser verification"
                    )
                fixed_sleep(SECURITY_WAIT_SECONDS, reason="列表页触发人工验证")
                continue

            verification_count = 0
            page_tasks = parse_search_page(
                page=page,
                source_page=page_no,
                parent_task_name=task.name,
                filter_config=task.filter.to_dict(),
            )

            if not page_tasks:
                print(f"[Task:{task.name}][List] page {page_no} no tasks, stop collect")
                break

            detail_tasks.extend(page_tasks)

            total_count = len(detail_tasks)
            skipped_count = sum(
                1 for task in detail_tasks if task.get("status") == TASK_STATUS_SKIPPED
            )
            pending_count = total_count - skipped_count

            print(
                f"[Task:{task.name}][List] page={page_no} collected={len(page_tasks)} "
                f"total={total_count}, pending={pending_count}, skipped={skipped_count}"
            )

            if page_no < max_pages:
                random_sleep(LIST_PAGE_DELAY_MIN, LIST_PAGE_DELAY_MAX)

            page_no += 1

        print(f"[Task:{task.name}][List] collect finished total={len(detail_tasks)}")

        return detail_tasks

    def run_detail_tasks(
        self,
        tasks: list[dict],
        task_name: str | None = None,
        on_detail_completed=None,
    ) -> list[dict]:
        total = len(tasks)
        verification_count = 0
        prefix = f"[Task:{task_name}]" if task_name else ""

        print(f"{prefix}[Detail] start tasks total={total}")

        index = 0

        while index < total:
            task = tasks[index]

            completed_count = sum(
                1 for item in tasks if item.get("status") == TASK_STATUS_COMPLETED
            )
            failed_count = sum(
                1 for item in tasks if item.get("status") == TASK_STATUS_FAILED
            )
            skipped_count = sum(
                1 for item in tasks if item.get("status") == TASK_STATUS_SKIPPED
            )

            if task.get("status") == TASK_STATUS_SKIPPED:
                print(
                    f"{prefix}[Detail] {index + 1}/{total} skipped "
                    f"name={task.get('name')} reason={task.get('reason')}"
                )
                index += 1
                continue

            url = task.get("url")

            if not url:
                task["status"] = TASK_STATUS_FAILED
                task["reason"] = "missing_url"
                print(f"{prefix}[Detail] {index + 1}/{total} failed: missing url")
                index += 1
                continue

            print(
                f"{prefix}[Detail] {index + 1}/{total} running "
                f"completed={completed_count} failed={failed_count} skipped={skipped_count} "
                f"name={task.get('name')} url={url}"
            )
            self.logger.info("Detail page: %s", url)

            task["status"] = TASK_STATUS_RUNNING

            try:
                page = self.fetch(url)

                if is_security_check_page(page):
                    verification_count += 1
                    task["status"] = TASK_STATUS_PENDING
                    print(
                        f"{prefix}[Security] detail task {index + 1}/{total} triggered verification, "
                        f"wait {SECURITY_WAIT_SECONDS}s and retry same task"
                    )
                    if verification_count >= 5:
                        print(
                            f"{prefix}[Security] continuous verification count={verification_count}, "
                            "please manually refresh cookies or complete browser verification"
                        )
                    fixed_sleep(SECURITY_WAIT_SECONDS, reason="详情页触发人工验证")
                    continue

                verification_count = 0
                detail = parse_detail_page(page)

                task["detail"] = detail
                task["status"] = TASK_STATUS_COMPLETED

                print(f"{prefix}[Detail] {index + 1}/{total} completed name={task.get('name')}")

                if on_detail_completed:
                    on_detail_completed(task)

                index += 1

                if index < total:
                    random_sleep(DETAIL_PAGE_DELAY_MIN, DETAIL_PAGE_DELAY_MAX)

            except Exception as exc:
                verification_count = 0
                task["status"] = TASK_STATUS_FAILED
                task["reason"] = str(exc)

                print(
                    f"{prefix}[Detail] {index + 1}/{total} failed "
                    f"name={task.get('name')} error={exc}"
                )

                index += 1

                if index < total:
                    random_sleep(DETAIL_PAGE_DELAY_MIN, DETAIL_PAGE_DELAY_MAX)

        completed_count = sum(1 for item in tasks if item.get("status") == TASK_STATUS_COMPLETED)
        failed_count = sum(1 for item in tasks if item.get("status") == TASK_STATUS_FAILED)
        skipped_count = sum(1 for item in tasks if item.get("status") == TASK_STATUS_SKIPPED)

        print(
            f"{prefix}[Detail] finished total={total} "
            f"completed={completed_count} failed={failed_count} skipped={skipped_count}"
        )

        return tasks

    def run_task(self, task: CrawlTask, on_detail_completed=None) -> list[dict]:
        if task.is_skip:
            print(f"[Task:{task.name}] skipped by config")
            return []

        if not task.final_url:
            print(f"[Task:{task.name}] skipped: missing final_url")
            return []

        detail_tasks = self.collect_detail_tasks(task)
        return self.run_detail_tasks(
            detail_tasks,
            task_name=task.name,
            on_detail_completed=on_detail_completed,
        )

    def run(self, task: CrawlTask) -> list[dict]:
        return self.run_task(task)
