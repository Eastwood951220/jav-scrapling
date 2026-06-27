"""Storage task state machine — orchestrates the pipeline steps."""

from __future__ import annotations

import random
from datetime import timedelta

from shared.common.datetime import utc_now

PIPELINE_STEPS = [
    "prepare",
    "submit_magnet",
    "waiting_download",
    "scan_files",
    "select_videos",
    "rename_files",
    "move_files",
    "verify_result",
    "cleanup_files",
]


class StorageStateMachine:
    def __init__(self, steps: list) -> None:
        self.steps = {step.name: step for step in steps}

    def execute(self, context) -> None:
        task = context.task
        task_id = task["task_id"]
        start_step = task.get("step") or "prepare"
        start_index = PIPELINE_STEPS.index(start_step) if start_step in PIPELINE_STEPS else 0

        context.task_repository.update(task_id, {"status": "running", "step": start_step, "error_message": None})
        context.movie_repository.update_storage_summary(task["movie_id"], task_id, "running", current_step=start_step)

        for index in range(start_index, len(PIPELINE_STEPS)):
            step_name = PIPELINE_STEPS[index]
            step = self.steps[step_name]
            context.task_repository.update(task_id, {"step": step_name, "progress": index / len(PIPELINE_STEPS)})

            if step.is_completed(context):
                context.logger.log(f"步骤 {step_name} 已完成，跳过", step=step_name)
                continue

            try:
                context.logger.log(f"执行步骤: {step_name}", step=step_name)
                context.task = step.execute(context)
            except Exception as exc:
                self._handle_failure(context, step_name, exc)
                return

        final_files = context.task.get("moved_files", [])
        context.task_repository.mark_completed(task_id, final_files)
        context.movie_repository.update_storage_summary(task["movie_id"], task_id, "completed", final_files=final_files)
        context.logger.log("任务全部完成")

    def _handle_failure(self, context, step_name: str, exc: Exception) -> None:
        task = context.task
        attempt = task.get("step_attempt", 0) + 1
        max_retries = context.config.get("max_step_retries", 3)
        retryable = attempt < max_retries

        if retryable:
            delay = random.uniform(
                context.config.get("retry_delay_min", 10.0),
                context.config.get("retry_delay_max", 30.0),
            )
            context.task_repository.update(
                task["task_id"],
                {
                    "status": "waiting_retry",
                    "step": step_name,
                    "step_attempt": attempt,
                    "retry_count": task.get("retry_count", 0) + 1,
                    "error_message": str(exc),
                    "retry.next_retry_at": utc_now() + timedelta(seconds=delay),
                },
            )
            context.logger.log(f"将在 {delay:.0f}s 后重试步骤 {step_name}", "ERROR", step_name)
        else:
            context.task_repository.mark_failed(
                task["task_id"],
                step_name,
                {"message": str(exc), "type": exc.__class__.__name__},
                retryable=True,
            )
            context.movie_repository.update_storage_summary(task["movie_id"], task["task_id"], "retryable")
