"""Integration test: multi-target copy/move pipeline."""

from unittest.mock import MagicMock, patch

from app.modules.storage.tasks.worker import _step_move_files


PATCH_PREFIX = "app.modules.storage.tasks.worker"


def _build_task(task_id, target_paths, selected_videos):
    """Build a minimal task dict for _step_move_files."""
    return {
        "task_id": task_id,
        "target_path": target_paths[-1],
        "target_paths": target_paths,
        "selected_videos": selected_videos,
    }


def _run_step(task, config=None):
    """Run _step_move_files with standard mocks applied via context managers."""
    mock_cd2 = MagicMock()
    mock_cd2.find_file_by_path.return_value = None
    mock_cd2.create_folder.return_value = None
    mock_cd2.copy_file.return_value = MagicMock()
    mock_cd2.move_file.return_value = MagicMock()

    cfg = config or {"auto_create_target_folder": True}

    with patch(f"{PATCH_PREFIX}._build_cd2_client", return_value=mock_cd2), \
         patch(f"{PATCH_PREFIX}._check_stop", return_value=False), \
         patch(f"{PATCH_PREFIX}._get_file_info", return_value=None), \
         patch(f"{PATCH_PREFIX}._append_log"), \
         patch(f"{PATCH_PREFIX}._update_task"):
        result = _step_move_files(task, cfg)

    return result, mock_cd2


# ---------------------------------------------------------------------------
# 1. Single target: only move, no copy
# ---------------------------------------------------------------------------


def test_single_target_uses_move_only():
    """Single target_path -> only move, no copy."""
    task = _build_task(
        "T001",
        ["/Movies/taskA/ABC-001"],
        [{"path": "/Downloads/T001/ABC-001.mp4", "renamed_path": "/Downloads/T001/ABC-001.mp4", "size": 1024}],
    )

    result, mock_cd2 = _run_step(task)

    assert mock_cd2.copy_file.call_count == 0
    assert mock_cd2.move_file.call_count == 1
    assert result["moved_files"][0]["copied_paths"] == []
    assert result["moved_files"][0]["moved_path"] == "/Movies/taskA/ABC-001/ABC-001.mp4"


# ---------------------------------------------------------------------------
# 2. Two targets: copy to first, move to second
# ---------------------------------------------------------------------------


def test_two_targets_copy_first_move_second():
    """Two targets -> copy to first, move to second."""
    task = _build_task(
        "T002",
        ["/Movies/taskA/ABC-001", "/Movies/taskB/ABC-001"],
        [{"path": "/Downloads/T002/ABC-001.mp4", "renamed_path": "/Downloads/T002/ABC-001.mp4", "size": 2048}],
    )

    result, mock_cd2 = _run_step(task)

    assert mock_cd2.copy_file.call_count == 1
    assert mock_cd2.move_file.call_count == 1
    assert len(result["moved_files"][0]["copied_paths"]) == 1

    # Verify correct arguments
    src = "/Downloads/T002/ABC-001.mp4"
    mock_cd2.copy_file.assert_called_once_with([src], "/Movies/taskA/ABC-001")
    mock_cd2.move_file.assert_called_once_with([src], "/Movies/taskB/ABC-001")


# ---------------------------------------------------------------------------
# 3. Three targets: copy to first two, move to last
# ---------------------------------------------------------------------------


def test_three_targets_copy_two_move_last():
    """Three targets -> copy to first two, move to last."""
    task = _build_task(
        "T003",
        ["/Movies/taskA/ABC-001", "/Movies/taskB/ABC-001", "/Movies/taskC/ABC-001"],
        [{"path": "/Downloads/T003/ABC-001.mp4", "renamed_path": "/Downloads/T003/ABC-001.mp4", "size": 4096}],
    )

    result, mock_cd2 = _run_step(task)

    assert mock_cd2.copy_file.call_count == 2
    assert mock_cd2.move_file.call_count == 1
    assert len(result["moved_files"][0]["copied_paths"]) == 2


# ---------------------------------------------------------------------------
# 4. Multiple videos with multiple targets
# ---------------------------------------------------------------------------


def test_multi_video_multi_target():
    """Multiple videos x multiple targets: each video copied then moved."""
    task = _build_task(
        "T004",
        ["/Movies/taskA/ABC-001", "/Movies/taskB/ABC-001"],
        [
            {"path": "/D/T004/ABC-001-CD1.mp4", "renamed_path": "/D/T004/ABC-001-CD1.mp4", "size": 100},
            {"path": "/D/T004/ABC-001-CD2.mp4", "renamed_path": "/D/T004/ABC-001-CD2.mp4", "size": 200},
        ],
    )

    result, mock_cd2 = _run_step(task)

    # 2 videos x 1 copy target = 2 copies
    assert mock_cd2.copy_file.call_count == 2
    # 2 videos x 1 move target = 2 moves
    assert mock_cd2.move_file.call_count == 2

    for f in result["moved_files"]:
        assert len(f["copied_paths"]) == 1
