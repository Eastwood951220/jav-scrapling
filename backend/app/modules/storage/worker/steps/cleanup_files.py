"""Cleanup files step — delete temp download folder and excluded files."""


class CleanupFilesStep:
    name = "cleanup_files"

    def is_completed(self, context) -> bool:
        return bool(context.task.get("cleaned"))

    def execute(self, context) -> dict:
        task = context.task
        task_id = task["task_id"]
        download_path = task.get("download_path")

        if download_path and context.config.get("use_task_subfolder", True):
            try:
                context.provider.delete_file(download_path)
                context.logger.log(f"已清理下载目录: {download_path}")
            except Exception as e:
                context.logger.log(f"清理下载目录失败 (非致命): {e}", "WARNING")

        context.task_repository.update(task_id, {"cleaned": True})
        context.logger.log("清理完成")

        return {**task, "cleaned": True}
