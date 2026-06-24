from pathlib import Path
from typing import Any

import yaml

from config.logging import get_logger
from config.settings import BASE_DIR, MAX_LIST_PAGES
from tasks.task_schema import CrawlTask, FilterConfig
from tasks.task_utils import build_final_url, determine_source, ensure_string

DEFAULT_TASK_FILE = BASE_DIR / "tasks" / "task.yml"


class TaskLoader:
    def __init__(self, config_file: str | Path = DEFAULT_TASK_FILE):
        self.config_file = Path(config_file)
        self.logger = get_logger("TaskLoader")

    def load_tasks(self) -> list[CrawlTask]:
        if not self.config_file.exists():
            self.logger.warning("任务配置文件不存在: %s", self.config_file)
            return []

        with self.config_file.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}

        tasks_data = data.get("tasks", [])

        if not tasks_data and "javdb" in data:
            tasks_data = self._build_fallback_tasks(data)

        if not isinstance(tasks_data, list):
            self.logger.warning("tasks 必须是列表")
            return []

        result: list[CrawlTask] = []

        for index, item in enumerate(tasks_data, start=1):
            if not isinstance(item, dict):
                self.logger.warning("第 %s 个任务不是字典，已跳过", index)
                continue

            try:
                task = self._parse_task(item)
                result.append(task)
            except Exception as exc:
                self.logger.warning("第 %s 个任务解析失败，已跳过: %s", index, exc)

        self.logger.info("成功加载 %s 个任务", len(result))

        return result

    def _build_fallback_tasks(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        javdb_config = data.get("javdb") or {}
        keyword = ensure_string(javdb_config.get("keyword"))

        if not keyword:
            return []

        return [
            {
                "name": keyword,
                "url": f"https://javdb.com/search?q={keyword}&f=all",
                "url_type": "search",
                "is_skip": not javdb_config.get("enabled", True),
                "max_list_pages": javdb_config.get("max_list_pages", MAX_LIST_PAGES),
                "filter": {},
            }
        ]

    def _parse_task(self, data: dict[str, Any]) -> CrawlTask:
        filter_data = data.get("filter") or {}

        if not isinstance(filter_data, dict):
            filter_data = {}

        known_filter_keys = {"only_chinese", "exclude_multi_person"}
        extra_filters = {
            key: value
            for key, value in filter_data.items()
            if key not in known_filter_keys
        }

        filter_config = FilterConfig(
            only_chinese=bool(filter_data.get("only_chinese", False)),
            exclude_multi_person=bool(filter_data.get("exclude_multi_person", False)),
            extra_filters=extra_filters,
        )

        raw_max_pages = int(data.get("max_list_pages", MAX_LIST_PAGES) or MAX_LIST_PAGES)
        max_list_pages = min(raw_max_pages, MAX_LIST_PAGES)

        url = ensure_string(data.get("url"))
        url_type = ensure_string(data.get("url_type"))
        source = data.get("source") or determine_source(url)
        final_url = build_final_url(
            url=url,
            url_type=url_type,
            filter_config=filter_config.to_dict(),
            source=source,
        )

        return CrawlTask(
            name=ensure_string(data.get("name")),
            url=url,
            url_type=url_type,
            is_skip=bool(data.get("is_skip", False)),
            max_list_pages=max_list_pages,
            filter=filter_config,
            source=source,
            final_url=final_url,
        )
