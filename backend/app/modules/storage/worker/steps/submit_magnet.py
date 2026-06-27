"""Submit magnet step — submit offline download to CloudDrive2."""

from shared.integrations.storage_providers.clouddrive2.exceptions import CloudDriveOperationError


def is_duplicate_magnet_error(error: Exception) -> bool:
    """Check if a CloudDrive error indicates the magnet was already submitted (code 10008)."""
    details = str(error)
    return "10008" in details or "任务已存在" in details


def _find_existing_download(provider, download_root: str) -> list:
    """Search download root for existing download files."""
    found_files = []
    try:
        entries = provider.list_files(download_root)
        for entry in entries:
            if entry.is_directory:
                try:
                    sub_files = provider.list_files(entry.full_path)
                    found_files.extend([f for f in sub_files if not f.is_directory])
                except Exception:
                    pass
            else:
                found_files.append(entry)
    except Exception:
        pass
    return found_files


class SubmitMagnetStep:
    name = "submit_magnet"

    def is_completed(self, context) -> bool:
        dl = context.task.get("download", {})
        return bool(dl.get("cd2_task_name") or dl.get("status") in ("submitted", "found_existing"))

    def execute(self, context) -> dict:
        task = context.task
        task_id = task["task_id"]
        magnet_url = task["magnet_url"]
        download_path = task["download_path"]

        try:
            context.provider.ensure_directory(download_path)
        except Exception:
            context.logger.log(f"下载目录已存在或无法提前创建: {download_path}", "WARNING", "submit_magnet")

        try:
            result = context.provider.submit_offline_download(magnet_url, download_path)
            download = {
                "status": "submitted",
                "result_paths": result.result_paths,
            }
            context.task_repository.update(task_id, {"download": download})
            context.logger.log("磁力链接已提交", step="submit_magnet")
            return {**task, "download": download}
        except CloudDriveOperationError as exc:
            if not is_duplicate_magnet_error(exc):
                raise

            context.logger.log(
                "磁力链接已存在 (code 10008)，搜索现有下载...",
                "WARNING",
                step="submit_magnet",
            )

            download_root = context.config.get("download_root_folder", "/Downloads")
            existing_files = _find_existing_download(context.provider, download_root)

            if existing_files:
                context.logger.log(
                    f"找到现有下载: {len(existing_files)} 个文件",
                    step="submit_magnet",
                )
                download = {
                    "status": "found_existing",
                    "found_files": len(existing_files),
                }
            else:
                context.logger.log(
                    "未找到现有文件，将在等待下载步骤中继续轮询",
                    "WARNING",
                    step="submit_magnet",
                )
                download = {
                    "status": "submitted_duplicate",
                    "found_files": 0,
                }

            context.task_repository.update(task_id, {"download": download})
            return {**task, "download": download}
