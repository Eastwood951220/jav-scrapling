"""Tests for _step_verify_result multi-target verification."""

from unittest.mock import MagicMock, patch

from app.modules.storage.tasks.worker import _step_verify_result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(moved_files, target_path="/Movies/taskB/ABC-001"):
    """Build a minimal task dict for _step_verify_result."""
    return {
        "task_id": "T001",
        "target_path": target_path,
        "target_paths": ["/Movies/taskA/ABC-001", target_path],
        "moved_files": moved_files,
    }


def _mock_cd2():
    """Build a mock CloudDriveGrpcClient."""
    cd2 = MagicMock()
    return cd2


def _mock_file_info(size=1024):
    """Build a mock file info dict (as returned by _get_file_info)."""
    return {"name": "ABC-001.mp4", "path": "/test", "size": size, "is_dir": False}


# ---------------------------------------------------------------------------
# Verify checks both moved_path AND copied_paths
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._get_file_info")
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_verify_checks_all_targets(mock_build, mock_info, mock_log, mock_update):
    """Verify should check files exist in ALL target folders (move + copy)."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    # _get_file_info returns valid info for any path
    mock_info.return_value = _mock_file_info(1024)

    task = _make_task([
        {
            "name": "ABC-001.mp4",
            "size": 1024,
            "moved_path": "/Movies/taskB/ABC-001/ABC-001.mp4",
            "copied_paths": ["/Movies/taskA/ABC-001/ABC-001.mp4"],
        },
    ])

    result = _step_verify_result(task, {})

    assert result["verified"] is True
    # Should have checked both move target AND copy target
    assert mock_info.call_count == 2


# ---------------------------------------------------------------------------
# Single target (no copied_paths) still works
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._get_file_info")
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_verify_single_target_no_copies(mock_build, mock_info, mock_log, mock_update):
    """Verify works with single target (empty copied_paths)."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    mock_info.return_value = _mock_file_info(1024)

    task = _make_task([
        {
            "name": "ABC-001.mp4",
            "size": 1024,
            "moved_path": "/Movies/taskB/ABC-001/ABC-001.mp4",
            "copied_paths": [],
        },
    ])

    result = _step_verify_result(task, {})

    assert result["verified"] is True
    # Only moved_path checked
    assert mock_info.call_count == 1


# ---------------------------------------------------------------------------
# Copied file missing causes failure
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._get_file_info")
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_verify_fails_when_copied_file_missing(mock_build, mock_info, mock_log, mock_update):
    """Verify fails when a copied_path file does not exist."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    # moved_path exists, copied_path does not
    def side_effect(cd2, path):
        if "taskA" in path:
            return None
        return _mock_file_info(1024)

    mock_info.side_effect = side_effect

    task = _make_task([
        {
            "name": "ABC-001.mp4",
            "size": 1024,
            "moved_path": "/Movies/taskB/ABC-001/ABC-001.mp4",
            "copied_paths": ["/Movies/taskA/ABC-001/ABC-001.mp4"],
        },
    ])

    try:
        _step_verify_result(task, {})
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        pass

    mock_update.assert_called_once()
    update_args = mock_update.call_args[0]
    assert update_args[1]["verified"] is False


# ---------------------------------------------------------------------------
# Moved file missing causes failure
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._get_file_info")
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_verify_fails_when_moved_file_missing(mock_build, mock_info, mock_log, mock_update):
    """Verify fails when the moved_path file does not exist."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    mock_info.return_value = None

    task = _make_task([
        {
            "name": "ABC-001.mp4",
            "size": 1024,
            "moved_path": "/Movies/taskB/ABC-001/ABC-001.mp4",
            "copied_paths": ["/Movies/taskA/ABC-001/ABC-001.mp4"],
        },
    ])

    try:
        _step_verify_result(task, {})
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        pass

    mock_update.assert_called_once()
    assert mock_update.call_args[0][1]["verified"] is False


# ---------------------------------------------------------------------------
# Size mismatch causes failure
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._get_file_info")
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_verify_fails_on_size_mismatch(mock_build, mock_info, mock_log, mock_update):
    """Verify fails when file size does not match expected."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    # Return a file with wrong size
    mock_info.return_value = _mock_file_info(9999)

    task = _make_task([
        {
            "name": "ABC-001.mp4",
            "size": 1024,
            "moved_path": "/Movies/taskB/ABC-001/ABC-001.mp4",
            "copied_paths": [],
        },
    ])

    try:
        _step_verify_result(task, {})
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        pass

    mock_update.assert_called_once()
    assert mock_update.call_args[0][1]["verified"] is False


# ---------------------------------------------------------------------------
# Multiple files — all must pass
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._get_file_info")
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_verify_multiple_files_all_pass(mock_build, mock_info, mock_log, mock_update):
    """All files (move + copy) must pass verification."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    mock_info.return_value = _mock_file_info(1024)

    task = _make_task([
        {
            "name": "ABC-001.mp4",
            "size": 1024,
            "moved_path": "/Movies/taskB/ABC-001/ABC-001.mp4",
            "copied_paths": ["/Movies/taskA/ABC-001/ABC-001.mp4"],
        },
        {
            "name": "ABC-001-CD2.mp4",
            "size": 2048,
            "moved_path": "/Movies/taskB/ABC-001/ABC-001-CD2.mp4",
            "copied_paths": ["/Movies/taskA/ABC-001/ABC-001-CD2.mp4"],
        },
    ])

    result = _step_verify_result(task, {})

    assert result["verified"] is True
    # 2 files x 2 paths each = 4 checks
    assert mock_info.call_count == 4


# ---------------------------------------------------------------------------
# No moved_files — empty list passes
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_verify_empty_moved_files(mock_build, mock_log, mock_update):
    """Empty moved_files list should pass verification."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    task = _make_task([])

    result = _step_verify_result(task, {})

    assert result["verified"] is True
    mock_update.assert_called_once_with("T001", {"verified": True})


# ---------------------------------------------------------------------------
# Copied file size mismatch causes failure
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._get_file_info")
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_verify_fails_on_copied_file_size_mismatch(mock_build, mock_info, mock_log, mock_update):
    """Verify fails when a copied_path file has wrong size."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    # moved_path has correct size, copied_path has wrong size
    def side_effect(cd2, path):
        if "taskA" in path:
            return _mock_file_info(9999)  # wrong size
        return _mock_file_info(1024)  # correct size

    mock_info.side_effect = side_effect

    task = _make_task([
        {
            "name": "ABC-001.mp4",
            "size": 1024,
            "moved_path": "/Movies/taskB/ABC-001/ABC-001.mp4",
            "copied_paths": ["/Movies/taskA/ABC-001/ABC-001.mp4"],
        },
    ])

    try:
        _step_verify_result(task, {})
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        pass

    mock_update.assert_called_once()
    assert mock_update.call_args[0][1]["verified"] is False


# ---------------------------------------------------------------------------
# Log messages include label (moved/copied) for debugging
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
@patch("app.modules.storage.tasks.worker._get_file_info")
@patch("app.modules.storage.tasks.worker._build_cd2_client")
def test_verify_log_includes_label(mock_build, mock_info, mock_log, mock_update):
    """Error logs should include 'moved' or 'copied' label for debugging."""
    mock_cd2 = _mock_cd2()
    mock_build.return_value = mock_cd2

    # moved_path exists, copied_path does not
    def side_effect(cd2, path):
        if "taskA" in path:
            return None
        return _mock_file_info(1024)

    mock_info.side_effect = side_effect

    task = _make_task([
        {
            "name": "ABC-001.mp4",
            "size": 1024,
            "moved_path": "/Movies/taskB/ABC-001/ABC-001.mp4",
            "copied_paths": ["/Movies/taskA/ABC-001/ABC-001.mp4"],
        },
    ])

    try:
        _step_verify_result(task, {})
    except RuntimeError:
        pass

    # Find the error log about copied file missing
    # _append_log(task_id, message, level, ...) — level is 3rd positional arg
    error_calls = [
        c for c in mock_log.call_args_list
        if len(c[0]) >= 3 and c[0][2] == "ERROR"
    ]
    assert any("copied" in str(c) for c in error_calls), (
        f"Expected 'copied' label in error logs, got: {error_calls}"
    )
