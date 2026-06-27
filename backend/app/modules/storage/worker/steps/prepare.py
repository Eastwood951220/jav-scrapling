"""Prepare step — load movie data and validate prerequisites."""

from bson import ObjectId
from bson.errors import InvalidId

from app.modules.storage.domain.filename_policy import derive_code_suffix, derive_code_suffix_from_filename
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

        # Derive code suffix from magnet metadata
        code_suffix = ""
        magnet = context.magnet_repository.find_by_url(magnet_url)
        if magnet:
            code_suffix = derive_code_suffix(
                has_chinese_sub=magnet.get("has_chinese_sub", False),
                tags=magnet.get("tags", []),
            )
            context.logger.log(f"从磁力元数据推导后缀: {code_suffix or '(无)'}")
        else:
            context.logger.log(f"未找到磁力记录: {magnet_url[:50]}...", "WARNING")

        # Fallback: try to derive suffix from original filename
        if not code_suffix:
            selected_videos = task.get("selected_videos", [])
            if selected_videos:
                original_name = selected_videos[0].get("name", "")
                code_suffix = derive_code_suffix_from_filename(original_name)
                if code_suffix:
                    context.logger.log(f"从原始文件名推导后缀: {code_suffix}")

        source_task_name = movie.get("source_task_name", "")
        task_with_name = {**task, "source_task_name": source_task_name}
        download_path = download_folder(task, context.config)
        target_path = target_folder(task_with_name, context.config, code_suffix)
        target_paths = all_target_folders(task_with_name, context.config, code_suffix)

        context.task_repository.update(
            task_id,
            {
                "download_path": download_path,
                "target_path": target_path,
                "target_paths": target_paths,
                "magnet_url": magnet_url,
                "source_task_name": source_task_name,
                "code_suffix": code_suffix,
            },
        )
        context.logger.log(f"准备完成: download={download_path}, target={target_path}, targets={target_paths}, suffix={code_suffix}")

        return {
            **task_with_name,
            "download_path": download_path,
            "target_path": target_path,
            "target_paths": target_paths,
            "magnet_url": magnet_url,
            "code_suffix": code_suffix,
        }
