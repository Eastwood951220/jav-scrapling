"""Select videos step — filter scanned files by extension and size."""

from app.modules.storage.domain.video_selector import select_files


class SelectVideosStep:
    name = "select_videos"

    def is_completed(self, context) -> bool:
        return bool(context.task.get("selected_videos"))

    def execute(self, context) -> dict:
        task = context.task
        task_id = task["task_id"]
        scanned = task.get("scanned_files", [])

        result = select_files(scanned, context.config)

        context.task_repository.update(
            task_id,
            {
                "selected_videos": result.selected_videos,
                "excluded_files": result.excluded_files,
                "subtitle_files": result.subtitle_files,
                "cover_files": result.cover_files,
            },
        )

        context.logger.log(
            f"文件筛选: videos={len(result.selected_videos)}, "
            f"excluded={len(result.excluded_files)}, "
            f"subtitles={len(result.subtitle_files)}, "
            f"covers={len(result.cover_files)}, "
            f"other={len(result.other_files)}"
        )

        return {
            **task,
            "selected_videos": result.selected_videos,
            "excluded_files": result.excluded_files,
            "subtitle_files": result.subtitle_files,
            "cover_files": result.cover_files,
        }
