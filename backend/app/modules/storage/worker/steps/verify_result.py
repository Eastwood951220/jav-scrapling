"""Verify result step — verify target files exist with correct sizes."""

from pathlib import PurePosixPath


class VerifyResultStep:
    name = "verify_result"

    def is_completed(self, context) -> bool:
        return bool(context.task.get("verified"))

    def execute(self, context) -> dict:
        task = context.task
        task_id = task["task_id"]
        moved_files = task.get("moved_files", [])

        all_ok = True
        for video in moved_files:
            paths_to_verify = []
            moved_path = video.get("moved_path")
            if moved_path:
                paths_to_verify.append(("moved", moved_path))
            for cp in video.get("copied_paths", []):
                paths_to_verify.append(("copied", cp))

            if not paths_to_verify:
                all_ok = False
                context.logger.log(f"验证失败: {video.get('name')} 无任何目标路径", "ERROR")
                continue

            expected_size = video.get("size", 0)
            for label, path in paths_to_verify:
                info = context.provider.find_file(path)
                if not info:
                    all_ok = False
                    context.logger.log(f"验证失败: {label} 文件不存在 {path}", "ERROR")
                    continue

                actual_size = info.size
                if expected_size > 0 and abs(actual_size - expected_size) > 1024:
                    all_ok = False
                    context.logger.log(
                        f"验证失败: {label} 大小不匹配 {PurePosixPath(path).name} "
                        f"(expected={expected_size}, actual={actual_size})",
                        "ERROR",
                    )

        context.task_repository.update(task_id, {"verified": all_ok})

        if all_ok:
            context.logger.log("验证通过: 所有文件完整 (含复制目标)")
        else:
            raise RuntimeError("文件验证失败")

        return {**task, "verified": all_ok}
