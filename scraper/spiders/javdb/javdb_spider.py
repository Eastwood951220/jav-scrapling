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
from scraper.tasks.task_schema import CrawlTask, CrawlTaskUrlEntry


class JavdbSpider(BaseSpider):
    name = "javdb"

    def __init__(self, fetcher):
        super().__init__(fetcher)
        self.logger = get_logger(self.name)

    @staticmethod
    def _emit(message: str, log_callback=None, level: str = "INFO") -> None:
        print(message)
        if log_callback:
            log_callback(message, level)

    def collect_detail_tasks_for_url(
        self,
        url_entry: CrawlTaskUrlEntry,
        task_name: str,
        stop_check=None,
        log_callback=None,
        on_tasks_batch_created=None,
    ) -> list[dict]:
        """Collect detail tasks from list pages for a single URL entry."""
        max_pages = MAX_LIST_PAGES
        detail_tasks: list[dict] = []
        seen_codes: set[str] = set()
        verification_count = 0

        final_url = url_entry.final_url or url_entry.url
        msg = f"[{task_name}] 开始收集列表页 url={final_url}, 最大页数={max_pages}"
        self._emit(msg, log_callback)

        page_no = 1

        while page_no <= max_pages:
            if stop_check and stop_check():
                msg = f"[{task_name}] 列表页 {page_no} 收到停止信号"
                self._emit(msg, log_callback, "WARNING")
                break
            page_url = build_task_page_url(final_url, page_no)
            msg = f"[{task_name}] 正在获取列表页 {page_no}/{max_pages}"
            self._emit(msg, log_callback)
            self.logger.info("List page: %s", page_url)

            page = self.fetch(page_url)

            if is_security_check_page(page):
                verification_count += 1
                msg = (
                    f"[{task_name}] 列表页 {page_no} 触发安全验证, "
                    f"等待 {SECURITY_WAIT_SECONDS}s 后重试"
                )
                self._emit(msg, log_callback, "WARNING")
                if verification_count >= 5:
                    msg = (
                        f"[{task_name}] 连续验证次数={verification_count}, "
                        "请手动刷新 cookies 或完成浏览器验证"
                    )
                    self._emit(msg, log_callback, "ERROR")
                fixed_sleep(SECURITY_WAIT_SECONDS, reason="列表页触发人工验证")
                continue

            verification_count = 0
            page_tasks = parse_search_page(
                page=page,
                source_page=page_no,
            )

            if not page_tasks:
                msg = f"[{task_name}] 列表页 {page_no} 无数据, 停止收集"
                self._emit(msg, log_callback)
                break

            # Dedup: filter out codes already seen in this URL
            fresh_tasks: list[dict] = []
            for t in page_tasks:
                code = t.get("code")
                if code and code in seen_codes:
                    continue
                if code:
                    seen_codes.add(code)
                fresh_tasks.append(t)

            detail_tasks.extend(fresh_tasks)

            if on_tasks_batch_created and fresh_tasks:
                on_tasks_batch_created(fresh_tasks)

            total_count = len(detail_tasks)
            skipped_count = sum(
                1 for t in detail_tasks if t.get("status") == TASK_STATUS_SKIPPED
            )
            pending_count = total_count - skipped_count

            msg = (
                f"[{task_name}] 列表页 {page_no} 完成: 本页={len(fresh_tasks)}条(去重后), "
                f"总计={total_count}, 待处理={pending_count}, 跳过={skipped_count}"
            )
            self._emit(msg, log_callback)

            if page_no < max_pages:
                random_sleep(LIST_PAGE_DELAY_MIN, LIST_PAGE_DELAY_MAX)

            page_no += 1

        msg = f"[{task_name}] URL 列表收集完成: 共 {len(detail_tasks)} 条任务"
        self._emit(msg, log_callback)

        return detail_tasks

    def collect_all_detail_tasks(
        self,
        task: CrawlTask,
        stop_check=None,
        log_callback=None,
        on_tasks_batch_created=None,
    ) -> list[dict]:
        """Collect detail tasks from ALL URLs in a task sequentially."""
        all_detail_tasks: list[dict] = []
        seen_codes: set[str] = set()

        for i, url_entry in enumerate(task.urls, 1):
            if stop_check and stop_check():
                msg = f"[{task.name}] URL {i}/{len(task.urls)} 收到停止信号"
                self._emit(msg, log_callback, "WARNING")
                break

            msg = f"[{task.name}] 处理 URL {i}/{len(task.urls)}: {url_entry.url_type}"
            self._emit(msg, log_callback)

            url_tasks = self.collect_detail_tasks_for_url(
                url_entry=url_entry,
                task_name=task.name,
                stop_check=stop_check,
                log_callback=log_callback,
                on_tasks_batch_created=on_tasks_batch_created,
            )

            # Dedup within this run: skip codes already seen
            for t in url_tasks:
                code = t.get("code")
                if code and code in seen_codes:
                    continue
                if code:
                    seen_codes.add(code)
                all_detail_tasks.append(t)

        msg = f"[{task.name}] 所有 URL 列表收集完成: 共 {len(all_detail_tasks)} 条唯一任务"
        self._emit(msg, log_callback)

        return all_detail_tasks

    def run_detail_tasks(
        self,
        tasks: list[dict],
        task_name: str | None = None,
        on_detail_completed=None,
        on_detail_failed=None,
        stop_check=None,
        log_callback=None,
    ) -> list[dict]:
        total = len(tasks)
        verification_count = 0
        prefix = f"[{task_name}]" if task_name else ""

        msg = f"{prefix} 开始处理详情页: 共 {total} 条"
        self._emit(msg, log_callback)

        index = 0

        while index < total:
            if stop_check and stop_check():
                msg = f"{prefix} 详情页 {index + 1}/{total} 收到停止信号"
                self._emit(msg, log_callback, "WARNING")
                break
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
                msg = (
                    f"{prefix} 详情 {index + 1}/{total} 跳过: "
                    f"name={task.get('name')} reason={task.get('reason')}"
                )
                self._emit(msg, log_callback)
                index += 1
                continue

            url = task.get("url")

            if not url:
                task["status"] = TASK_STATUS_FAILED
                task["reason"] = "missing_url"
                msg = f"{prefix} 详情 {index + 1}/{total} 失败: 缺少URL"
                self._emit(msg, log_callback, "ERROR")
                index += 1
                continue

            msg = (
                f"{prefix} 详情 {index + 1}/{total} 处理中: "
                f"已完成={completed_count} 失败={failed_count} 跳过={skipped_count} "
                f"name={task.get('name')}"
            )
            self._emit(msg, log_callback)
            self.logger.info("Detail page: %s", url)

            task["status"] = TASK_STATUS_RUNNING

            try:
                page = self.fetch(url)

                if is_security_check_page(page):
                    verification_count += 1
                    task["status"] = TASK_STATUS_PENDING
                    msg = (
                        f"{prefix} 详情 {index + 1}/{total} 触发安全验证, "
                        f"等待 {SECURITY_WAIT_SECONDS}s 后重试"
                    )
                    self._emit(msg, log_callback, "WARNING")
                    if verification_count >= 5:
                        msg = (
                            f"{prefix} 连续验证次数={verification_count}, "
                            "请手动刷新 cookies 或完成浏览器验证"
                        )
                        self._emit(msg, log_callback, "ERROR")
                    fixed_sleep(SECURITY_WAIT_SECONDS, reason="详情页触发人工验证")
                    continue

                verification_count = 0
                detail = parse_detail_page(page)

                task["detail"] = detail
                task["status"] = TASK_STATUS_COMPLETED

                msg = f"{prefix} 详情 {index + 1}/{total} 完成: {task.get('name')}"
                self._emit(msg, log_callback)

                if on_detail_completed:
                    on_detail_completed(task)

                index += 1

                if index < total:
                    random_sleep(DETAIL_PAGE_DELAY_MIN, DETAIL_PAGE_DELAY_MAX)

            except Exception as exc:
                verification_count = 0
                task["status"] = TASK_STATUS_FAILED
                task["reason"] = str(exc)

                if on_detail_failed:
                    on_detail_failed(task, str(exc))

                msg = f"{prefix} 详情 {index + 1}/{total} 失败: {task.get('name')} error={exc}"
                self._emit(msg, log_callback, "ERROR")

                index += 1

                if index < total:
                    random_sleep(DETAIL_PAGE_DELAY_MIN, DETAIL_PAGE_DELAY_MAX)

        completed_count = sum(1 for item in tasks if item.get("status") == TASK_STATUS_COMPLETED)
        failed_count = sum(1 for item in tasks if item.get("status") == TASK_STATUS_FAILED)
        skipped_count = sum(1 for item in tasks if item.get("status") == TASK_STATUS_SKIPPED)

        msg = (
            f"{prefix} 详情处理完成: 总计={total} "
            f"已完成={completed_count} 失败={failed_count} 跳过={skipped_count}"
        )
        self._emit(msg, log_callback)

        return tasks

    def run_task(self, task: CrawlTask, on_detail_completed=None, on_detail_failed=None, on_tasks_batch_created=None, stop_check=None, log_callback=None) -> list[dict]:
        if task.is_skip:
            print(f"[Task:{task.name}] skipped by config")
            return []

        if not task.urls:
            print(f"[Task:{task.name}] skipped: no URLs configured")
            return []

        # Phase 1: Collect all detail tasks from all URLs
        detail_tasks = self.collect_all_detail_tasks(
            task,
            stop_check=stop_check,
            log_callback=log_callback,
            on_tasks_batch_created=on_tasks_batch_created,
        )

        # Phase 2: Process all detail tasks
        return self.run_detail_tasks(
            detail_tasks,
            task_name=task.name,
            on_detail_completed=on_detail_completed,
            on_detail_failed=on_detail_failed,
            stop_check=stop_check,
            log_callback=log_callback,
        )

    def run(self, task: CrawlTask) -> list[dict]:
        return self.run_task(task)
