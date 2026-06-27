"""Prepare step — load movie data and validate prerequisites."""

from bson import ObjectId
from bson.errors import InvalidId

from app.modules.storage.domain.path_policy import all_target_folders, download_folder, target_folder


class PrepareStep:
    name = "prepare"

    def is_completed(self, context) -> bool:
        return bool(context.task.get("download_path") and context.task.get("target_path"))

    def execute(self, context) -> dict:
        task = context.task
        task_id = task["task_id"]

        try:
            ObjectId(task["movie_id"])
        except (InvalidId, TypeError) as exc:
            raise ValueError(f"无效的 movie_id: {task['movie_id']}") from exc

        movie = context.movie_repository.get_by_id(task["movie_id"])
        if not movie:
            raise ValueError(f"未找到电影: {task['movie_id']}")

        magnet_url = task.get("magnet_url") or movie.get("magnet_url", "")
        if not magnet_url:
            raise ValueError("缺少磁力链接")

        source_task_name = movie.get("source_task_name", "")
        task_with_name = {**task, "source_task_name": source_task_name}
        download_path = download_folder(task, context.config)
        target_path = target_folder(task_with_name, context.config)
        target_paths = all_target_folders(task_with_name, context.config)

        context.task_repository.update(
            task_id,
            {
                "download_path": download_path,
                "target_path": target_path,
                "target_paths": target_paths,
                "magnet_url": magnet_url,
                "source_task_name": source_task_name,
            },
        )
        context.logger.log(f"准备完成: download={download_path}, target={target_path}, targets={target_paths}")

        return {
            **task_with_name,
            "download_path": download_path,
            "target_path": target_path,
            "target_paths": target_paths,
            "magnet_url": magnet_url,
        }
