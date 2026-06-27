"""Move files step — move renamed videos to target folder(s).

When multiple target_paths exist (from multiple source_task_name):
- Copy files to all targets EXCEPT the last one
- Move files to the LAST target (preserves the download folder for cleanup)
"""

from pathlib import PurePosixPath

from shared.integrations.storage_providers.clouddrive2.exceptions import CloudDriveNotFoundError


class MoveFilesStep:
    name = "move_files"

    def is_completed(self, context) -> bool:
        task = context.task
        target = task.get("target_path")
        if not target:
            return False
        try:
            files = context.provider.list_files(target)
            video_exts = set(context.config.get("video_extensions", []))
            return any(
                PurePosixPath(f.name).suffix.lower() in video_exts
                for f in files
                if not f.is_directory
            )
        except Exception:
            return False

    def _source_file_exists(self, context, src_path: str) -> bool:
        """Check if source file exists before attempting move."""
        try:
            existing = context.provider.find_file(src_path)
            return existing is not None
        except CloudDriveNotFoundError:
            return False
        except Exception:
            # For other errors, assume file exists and let move attempt handle it
            return True

    def _ensure_target_folder(self, context, folder_path: str) -> bool:
        """Ensure target folder exists, create parent directories if needed."""
        try:
            # Try to list the folder first
            context.provider.list_files(folder_path)
            return True
        except Exception:
            pass

        # Build list of directories to create (from root to target)
        parts = PurePosixPath(folder_path).parts
        current = ""
        dirs_to_create = []
        for part in parts:
            current = str(PurePosixPath(current) / part) if current else part
            if current and current != "/":
                dirs_to_create.append(current)

        # Create directories in order (parent first)
        for dir_path in dirs_to_create:
            try:
                context.provider.list_files(dir_path)
            except Exception:
                try:
                    context.provider.ensure_directory(dir_path)
                    context.logger.log(f"已创建文件夹: {dir_path}")
                except Exception as e:
                    # Ignore if already exists
                    if "已存在" not in str(e) and "already exists" not in str(e).lower():
                        context.logger.log(f"创建文件夹失败: {dir_path}: {e}", "WARNING")

        # Verify the target folder exists now
        try:
            context.provider.list_files(folder_path)
            return True
        except Exception as e:
            context.logger.log(f"目标文件夹不存在: {folder_path}: {e}", "ERROR")
            return False

    def execute(self, context) -> dict:
        task = context.task
        task_id = task["task_id"]
        selected = task.get("selected_videos", [])
        target_path = task["target_path"]
        target_paths = task.get("target_paths", [target_path])

        files_to_move = list(selected)

        if not files_to_move:
            context.logger.log("无需移动，没有文件")
            return task

        copy_targets = target_paths[:-1] if len(target_paths) > 1 else []
        move_target = target_paths[-1]

        # Ensure all target folders exist
        if context.config.get("auto_create_target_folder", True):
            for tp in target_paths:
                if not self._ensure_target_folder(context, tp):
                    raise ValueError(f"无法创建目标文件夹: {tp}")

        moved = []
        skipped = []
        for f in files_to_move:
            # Skip files that failed to rename
            if f.get("rename_error"):
                context.logger.log(f"跳过重命名失败的文件: {f['name']}", "WARNING")
                skipped.append({**f, "skip_reason": "rename_failed"})
                continue

            src = f.get("renamed_path") or f["path"]
            file_name = PurePosixPath(src).name
            dst = str(PurePosixPath(move_target) / file_name)

            # Check if source file exists before attempting move
            if not self._source_file_exists(context, src):
                context.logger.log(f"跳过不存在的源文件: {file_name}", "WARNING")
                skipped.append({**f, "skip_reason": "source_not_found"})
                continue

            # Idempotent: skip if target file already exists
            existing = context.provider.find_file(dst)
            if existing and existing.size > 0:
                context.logger.log(f"跳过已存在: {file_name}")
                moved.append({**f, "moved_path": dst, "copied_paths": []})
                continue

            # Copy to all targets except the last
            copied_paths = []
            for ct in copy_targets:
                copy_dst = str(PurePosixPath(ct) / file_name)
                try:
                    context.provider.move_files([src], ct)
                    copied_paths.append(copy_dst)
                    context.logger.log(f"已复制: {file_name} → {ct}")
                except Exception as e:
                    context.logger.log(f"复制失败: {file_name} → {ct}: {e}", "ERROR")
                    raise

            # Move to last target
            try:
                context.provider.move_files([src], move_target)
                moved.append({**f, "moved_path": dst, "copied_paths": copied_paths})
                context.logger.log(f"已移动: {file_name} → {move_target}")
            except Exception as e:
                context.logger.log(f"移动失败: {file_name}: {e}", "ERROR")
                raise

        if skipped:
            context.logger.log(f"跳过 {len(skipped)} 个不存在的文件", "WARNING")

        context.task_repository.update(task_id, {"moved_files": moved, "skipped_files": skipped})
        return {**task, "moved_files": moved, "skipped_files": skipped}
