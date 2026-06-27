"""Wait download step — poll download folder until files appear."""

import random
import time


class WaitDownloadStep:
    name = "waiting_download"

    def is_completed(self, context) -> bool:
        return False

    def execute(self, context) -> dict:
        task = context.task
        task_id = task["task_id"]
        download_path = task.get("download_path", "")

        if not download_path:
            raise ValueError("缺少 download_path，无法查询下载状态")

        poll_min = context.config.get("download_poll_interval_min", 5.0)
        poll_max = context.config.get("download_poll_interval_max", 15.0)
        max_wait_min = context.config.get("download_max_wait_minutes", 120)
        deadline = time.monotonic() + max_wait_min * 60

        poll_count = 0
        while True:
            if time.monotonic() > deadline:
                raise RuntimeError(f"下载超时: 超过 {max_wait_min} 分钟")

            poll_count += 1
            try:
                entries = context.provider.list_files(download_path)
                if entries:
                    dir_count = sum(1 for e in entries if e.is_directory)
                    file_count = len(entries) - dir_count
                    total_size = sum(e.size for e in entries)

                    if dir_count > 0:
                        for d in [e for e in entries if e.is_directory]:
                            try:
                                sub_files = context.provider.list_files(d.full_path)
                                sub_non_dir = [f for f in sub_files if not f.is_directory]
                                if sub_non_dir:
                                    total_size += sum(f.size for f in sub_non_dir)
                                    file_count += len(sub_non_dir)
                            except Exception:
                                pass

                    context.task_repository.update(
                        task_id,
                        {
                            "download.status": "completed",
                            "download.progress": 100,
                            "progress": 100,
                        },
                    )
                    context.logger.log(
                        f"下载完成: 检测到 {file_count} 个文件, "
                        f"总大小 {total_size / (1024*1024):.1f} MB",
                        step="waiting_download",
                    )
                    return task

                context.logger.log(
                    f"轮询 #{poll_count}: 目录为空，等待中...",
                    step="waiting_download",
                )
            except Exception as exc:
                context.logger.log(
                    f"轮询 #{poll_count} 异常: {exc}",
                    "WARNING",
                    step="waiting_download",
                )

            poll_interval = random.uniform(poll_min, poll_max)
            time.sleep(poll_interval)
