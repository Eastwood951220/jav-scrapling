"""Rename files step — rename video files using the configured template."""

from pathlib import PurePosixPath

from app.modules.storage.domain.filename_policy import build_video_name


class RenameFilesStep:
    name = "rename_files"

    def is_completed(self, context) -> bool:
        selected = context.task.get("selected_videos", [])
        return bool(selected) and all(v.get("renamed_path") for v in selected)

    def execute(self, context) -> dict:
        task = context.task
        task_id = task["task_id"]
        selected = task.get("selected_videos", [])
        movie_code = task.get("movie_code", "UNKNOWN")
        code_suffix = task.get("code_suffix", "")

        if not selected:
            context.logger.log("无需重命名，没有选中的视频文件")
            return task

        multi = len(selected) > 1
        single_tpl = context.config.get("single_filename_template", "{code}{ext}")
        multi_tpl = context.config.get("multi_filename_template", "{code}{ext}")

        renamed = []
        for i, video in enumerate(selected):
            old_path = video["path"]

            if multi:
                new_name = build_video_name(
                    movie_code=movie_code,
                    original_name=video["name"],
                    index=i,
                    total=len(selected),
                    template=multi_tpl,
                    code_suffix=code_suffix,
                )
            else:
                new_name = build_video_name(
                    movie_code=movie_code,
                    original_name=video["name"],
                    index=0,
                    total=1,
                    template=single_tpl,
                    code_suffix=code_suffix,
                )

            new_path = str(PurePosixPath(old_path).parent / new_name)

            try:
                context.provider.rename_file(old_path, new_name)
                renamed.append({**video, "renamed_path": new_path, "renamed_name": new_name})
                context.logger.log(f"重命名: {video['name']} → {new_name}")
            except Exception as e:
                context.logger.log(f"重命名失败: {video['name']}: {e}", "ERROR")
                renamed.append({**video, "rename_error": str(e)})

        context.task_repository.update(task_id, {"selected_videos": renamed})
        return {**task, "selected_videos": renamed}
