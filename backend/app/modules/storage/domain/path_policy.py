"""Path policy — pure functions for computing download and target folder paths."""

from pathlib import PurePosixPath


def download_folder(task: dict, config: dict) -> str:
    """Return the CloudDrive2 path for a task's download folder."""
    root = config.get("download_root_folder", "/Downloads")
    if config.get("use_task_subfolder", True):
        return str(PurePosixPath(root) / task["task_id"])
    return root


def target_folder(task: dict, config: dict, code_suffix: str = "") -> str:
    """Return the CloudDrive2 path for a task's target folder.

    Structure: {target_folder}/{source_task_name}/{movie_code}{code_suffix}
    When source_task_name is a list, uses the LAST element.
    Falls back to movie_code if no task name is available.
    """
    target = config.get("target_folder", "/Movies")
    task_name = task.get("source_task_name", "")
    movie_code = task["movie_code"] + code_suffix

    if isinstance(task_name, list):
        task_name = task_name[-1] if task_name else ""

    if task_name:
        return str(PurePosixPath(target) / task_name / movie_code)
    return str(PurePosixPath(target) / movie_code)


def all_target_folders(task: dict, config: dict, code_suffix: str = "") -> list[str]:
    """Return ALL target folder paths when source_task_name is a list.

    For a single name or empty, returns a list with one element (same as target_folder).
    """
    target = config.get("target_folder", "/Movies")
    task_name = task.get("source_task_name", "")
    movie_code = task["movie_code"] + code_suffix

    if isinstance(task_name, list) and len(task_name) > 1:
        return [str(PurePosixPath(target) / name / movie_code) for name in task_name]
    return [target_folder(task, config, code_suffix)]
