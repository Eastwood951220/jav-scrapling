"""Tests for _step_move_files multi-target copy-then-move logic."""

from unittest.mock import MagicMock, patch

from app.modules.storage.tasks.worker import _step_move_files


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(target_paths, selected_videos):
    """Build a minimal task dict for _step_move_files."""
    return {
        "task_id": "T001",
        "target_path": target_paths[-1],
        "target_paths": target_paths,
        "selected_videos": selected_videos,
    }


def _mock_cd2():
    """Build a mock CloudDriveGrpcClient."""
    cd2 = MagicMock()
    cd2.create_folder.return_value = None
    cd2.copy_file.return_value = MagicMock()
    cd2.move_file.return_value = MagicMock()
    cd2.find_file_by_path.return_value = None  # target does not exist
    return cd2


SINGLE_VIDEO = [
    {"path": "/Downloads/T001/ABC-001.mp4", "renamed_path": "/Downloads/T001/ABC-001.mp4", "size": 1024},
]

MULTI_VIDEO = [
    {"path": "/Downloads/T001/ABC-001.mp4", "renamed_path": "/Downloads/T001/ABC-001.mp4", "size": 1024},
    {"path": "/Downloads/T001/ABC-001-CD2.mp4", "renamed_path": "/Downloads/T001/ABC-001-CD2.mp4", "size": 2048},
]


# ---------------------------------------------------------------------------
# 3 targets — copy to first 2, move to last
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._get_file_info", return_value=None)
@patch("app.modules.storage.tasks.worker._check_stop", return_value=False)
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_move_files_copies_to_all_but_last_target(
    mock_build, mock_stop, mock_info, mock_log, mock_update
):
    """When target_paths has 3 entries, copy to first 2, move to last."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    task = _make_task(
        ["/Movies/taskA/ABC-001", "/Movies/taskB/ABC-001", "/Movies/taskC/ABC-001"],
        SINGLE_VIDEO,
    )

    result = _step_move_files(task, {})

    # copy_file called 2 times (taskA, taskB)
    assert mock_cd2.copy_file.call_count == 2
    # move_file called 1 time (taskC)
    assert mock_cd2.move_file.call_count == 1

    # Verify copied_paths tracked
    moved = result["moved_files"][0]
    assert len(moved["copied_paths"]) == 2


# ---------------------------------------------------------------------------
# Single target — no copy, only move (backward compat)
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._get_file_info", return_value=None)
@patch("app.modules.storage.tasks.worker._check_stop", return_value=False)
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_move_files_single_target_no_copy(
    mock_build, mock_stop, mock_info, mock_log, mock_update
):
    """When target_paths has 1 entry, only move (no copy)."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    task = _make_task(
        ["/Movies/taskA/ABC-001"],
        SINGLE_VIDEO,
    )

    result = _step_move_files(task, {})

    # copy_file NOT called
    mock_cd2.copy_file.assert_not_called()
    # move_file called 1 time
    assert mock_cd2.move_file.call_count == 1

    moved = result["moved_files"][0]
    assert moved["copied_paths"] == []
    assert moved["moved_path"] == "/Movies/taskA/ABC-001/ABC-001.mp4"


# ---------------------------------------------------------------------------
# 2 targets — copy to first, move to last
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._get_file_info", return_value=None)
@patch("app.modules.storage.tasks.worker._check_stop", return_value=False)
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_move_files_two_targets(
    mock_build, mock_stop, mock_info, mock_log, mock_update
):
    """When target_paths has 2 entries, copy to first, move to last."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    task = _make_task(
        ["/Movies/taskA/ABC-001", "/Movies/taskB/ABC-001"],
        SINGLE_VIDEO,
    )

    result = _step_move_files(task, {})

    assert mock_cd2.copy_file.call_count == 1
    assert mock_cd2.move_file.call_count == 1

    moved = result["moved_files"][0]
    assert len(moved["copied_paths"]) == 1


# ---------------------------------------------------------------------------
# Idempotent skip — file already exists in move target
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._check_stop", return_value=False)
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_move_files_idempotent_skip(mock_build, mock_stop, mock_log, mock_update):
    """Skip file when it already exists in the move target."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    task = _make_task(
        ["/Movies/taskA/ABC-001", "/Movies/taskB/ABC-001"],
        SINGLE_VIDEO,
    )

    # Simulate file already exists at move target
    with patch(
        "app.modules.storage.tasks.worker._get_file_info",
        return_value={"name": "ABC-001.mp4", "size": 1024},
    ):
        result = _step_move_files(task, {})

    # Neither copy nor move should be called
    mock_cd2.copy_file.assert_not_called()
    mock_cd2.move_file.assert_not_called()

    moved = result["moved_files"][0]
    assert moved["copied_paths"] == []
    assert moved["moved_path"] == "/Movies/taskB/ABC-001/ABC-001.mp4"


# ---------------------------------------------------------------------------
# Multiple videos with multiple targets
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._get_file_info", return_value=None)
@patch("app.modules.storage.tasks.worker._check_stop", return_value=False)
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_move_files_multi_video_multi_target(
    mock_build, mock_stop, mock_info, mock_log, mock_update
):
    """Multiple videos with multiple targets: each video gets copied + moved."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    task = _make_task(
        ["/Movies/taskA/ABC-001", "/Movies/taskB/ABC-001", "/Movies/taskC/ABC-001"],
        MULTI_VIDEO,
    )

    result = _step_move_files(task, {})

    # 2 copies per video x 2 videos = 4
    assert mock_cd2.copy_file.call_count == 4
    # 1 move per video x 2 videos = 2
    assert mock_cd2.move_file.call_count == 2

    for moved in result["moved_files"]:
        assert len(moved["copied_paths"]) == 2


# ---------------------------------------------------------------------------
# Empty selected_videos
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._append_log")
def test_move_files_no_videos(mock_log):
    """No videos to move returns early."""
    task = _make_task(
        ["/Movies/taskA/ABC-001"],
        [],
    )

    result = _step_move_files(task, {})
    assert "moved_files" not in result


# ---------------------------------------------------------------------------
# Stop signal during copy loop
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._get_file_info", return_value=None)
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_move_files_stop_during_copy(mock_build, mock_info, mock_log, mock_update):
    """Stop signal during copy loop should abort early."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    task = _make_task(
        ["/Movies/taskA/ABC-001", "/Movies/taskB/ABC-001", "/Movies/taskC/ABC-001"],
        SINGLE_VIDEO,
    )

    # First _check_stop call returns True (aborts before any copy/move)
    with patch("app.modules.storage.tasks.worker._check_stop", return_value=True):
        result = _step_move_files(task, {})

    mock_cd2.copy_file.assert_not_called()
    mock_cd2.move_file.assert_not_called()


# ---------------------------------------------------------------------------
# Missing renamed_path falls back to path
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._get_file_info", return_value=None)
@patch("app.modules.storage.tasks.worker._check_stop", return_value=False)
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_move_files_falls_back_to_path(
    mock_build, mock_stop, mock_info, mock_log, mock_update
):
    """When renamed_path is missing, use path as source."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    video_no_rename = [{"path": "/Downloads/T001/ABC-001.mp4", "size": 1024}]
    task = _make_task(["/Movies/taskA/ABC-001"], video_no_rename)

    result = _step_move_files(task, {})

    # move_file should be called with the original path
    mock_cd2.move_file.assert_called_once_with(
        ["/Downloads/T001/ABC-001.mp4"], "/Movies/taskA/ABC-001"
    )
    assert result["moved_files"][0]["moved_path"] == "/Movies/taskA/ABC-001/ABC-001.mp4"


# ---------------------------------------------------------------------------
# create_folder called for all targets
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._get_file_info", return_value=None)
@patch("app.modules.storage.tasks.worker._check_stop", return_value=False)
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_move_files_creates_all_target_folders(
    mock_build, mock_stop, mock_info, mock_log, mock_update
):
    """create_folder is called for every target path, not just the move target."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    task = _make_task(
        ["/Movies/taskA/ABC-001", "/Movies/taskB/ABC-001", "/Movies/taskC/ABC-001"],
        SINGLE_VIDEO,
    )

    _step_move_files(task, {"auto_create_target_folder": True})

    # create_folder called for all 3 targets
    assert mock_cd2.create_folder.call_count == 3
    create_calls = [c[0][0] for c in mock_cd2.create_folder.call_args_list]
    assert "/Movies/taskA/ABC-001" in create_calls
    assert "/Movies/taskB/ABC-001" in create_calls
    assert "/Movies/taskC/ABC-001" in create_calls


# ---------------------------------------------------------------------------
# copy_file receives correct args
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._get_file_info", return_value=None)
@patch("app.modules.storage.tasks.worker._check_stop", return_value=False)
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_move_files_copy_args_correct(
    mock_build, mock_stop, mock_info, mock_log, mock_update
):
    """copy_file is called with [src_path] and target folder."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    task = _make_task(
        ["/Movies/taskA/ABC-001", "/Movies/taskB/ABC-001"],
        SINGLE_VIDEO,
    )

    _step_move_files(task, {})

    src = "/Downloads/T001/ABC-001.mp4"
    mock_cd2.copy_file.assert_called_once_with([src], "/Movies/taskA/ABC-001")
    mock_cd2.move_file.assert_called_once_with([src], "/Movies/taskB/ABC-001")
