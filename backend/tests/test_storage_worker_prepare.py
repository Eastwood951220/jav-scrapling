"""Tests for _target_folder and _all_target_folders multi-target support."""

from unittest.mock import patch

from app.modules.storage.tasks.worker import _all_target_folders, _target_folder


# ---------------------------------------------------------------------------
# _target_folder
# ---------------------------------------------------------------------------


def test_target_folder_single_name():
    """Single source_task_name produces one target path."""
    task = {"source_task_name": "taskA", "movie_code": "ABC-001"}
    config = {"target_folder": "/Movies"}
    result = _target_folder(task, config)
    assert result == "/Movies/taskA/ABC-001"


def test_target_folder_list_names():
    """List of source_task_name uses the LAST element."""
    task = {"source_task_name": ["taskA", "taskB"], "movie_code": "ABC-001"}
    config = {"target_folder": "/Movies"}
    result = _target_folder(task, config)
    assert result == "/Movies/taskB/ABC-001"


def test_target_folder_list_single_element():
    """List with one element behaves like a plain string."""
    task = {"source_task_name": ["taskA"], "movie_code": "ABC-001"}
    config = {"target_folder": "/Movies"}
    result = _target_folder(task, config)
    assert result == "/Movies/taskA/ABC-001"


def test_target_folder_empty_string():
    """Empty source_task_name falls back to movie_code only."""
    task = {"source_task_name": "", "movie_code": "ABC-001"}
    config = {"target_folder": "/Movies"}
    result = _target_folder(task, config)
    assert result == "/Movies/ABC-001"


def test_target_folder_missing_key():
    """Missing source_task_name falls back to movie_code only."""
    task = {"movie_code": "ABC-001"}
    config = {"target_folder": "/Movies"}
    result = _target_folder(task, config)
    assert result == "/Movies/ABC-001"


def test_target_folder_empty_list():
    """Empty list falls back to movie_code only."""
    task = {"source_task_name": [], "movie_code": "ABC-001"}
    config = {"target_folder": "/Movies"}
    result = _target_folder(task, config)
    assert result == "/Movies/ABC-001"


def test_target_folder_default_config():
    """Missing target_folder in config defaults to /Movies."""
    task = {"source_task_name": "taskA", "movie_code": "ABC-001"}
    result = _target_folder(task, {})
    assert result == "/Movies/taskA/ABC-001"


def test_target_folder_list_many_names():
    """List with many names always uses the last one."""
    task = {"source_task_name": ["a", "b", "c", "d"], "movie_code": "X-001"}
    config = {"target_folder": "/Library"}
    result = _target_folder(task, config)
    assert result == "/Library/d/X-001"


# ---------------------------------------------------------------------------
# _all_target_folders
# ---------------------------------------------------------------------------


def test_all_target_folders_single_name():
    """Single name returns a list with one element."""
    task = {"source_task_name": "taskA", "movie_code": "ABC-001"}
    config = {"target_folder": "/Movies"}
    result = _all_target_folders(task, config)
    assert result == ["/Movies/taskA/ABC-001"]


def test_all_target_folders_list_names():
    """List of names returns all paths."""
    task = {"source_task_name": ["taskA", "taskB"], "movie_code": "ABC-001"}
    config = {"target_folder": "/Movies"}
    result = _all_target_folders(task, config)
    assert result == ["/Movies/taskA/ABC-001", "/Movies/taskB/ABC-001"]


def test_all_target_folders_list_single_element():
    """List with one element returns a list with one path via fallback."""
    task = {"source_task_name": ["taskA"], "movie_code": "ABC-001"}
    config = {"target_folder": "/Movies"}
    result = _all_target_folders(task, config)
    assert result == ["/Movies/taskA/ABC-001"]


def test_all_target_folders_empty():
    """Empty string returns a list with one path (no task name prefix)."""
    task = {"source_task_name": "", "movie_code": "ABC-001"}
    config = {"target_folder": "/Movies"}
    result = _all_target_folders(task, config)
    assert result == ["/Movies/ABC-001"]


def test_all_target_folders_missing_key():
    """Missing key returns a list with one path."""
    task = {"movie_code": "ABC-001"}
    config = {"target_folder": "/Movies"}
    result = _all_target_folders(task, config)
    assert result == ["/Movies/ABC-001"]


def test_all_target_folders_empty_list():
    """Empty list returns a list with one path (fallback)."""
    task = {"source_task_name": [], "movie_code": "ABC-001"}
    config = {"target_folder": "/Movies"}
    result = _all_target_folders(task, config)
    assert result == ["/Movies/ABC-001"]


def test_all_target_folders_many_names():
    """List with many names returns all paths in order."""
    task = {"source_task_name": ["a", "b", "c"], "movie_code": "X-001"}
    config = {"target_folder": "/Lib"}
    result = _all_target_folders(task, config)
    assert result == ["/Lib/a/X-001", "/Lib/b/X-001", "/Lib/c/X-001"]


# ---------------------------------------------------------------------------
# _step_prepare integration (mocked MongoDB)
# ---------------------------------------------------------------------------


@patch("app.modules.storage.tasks.worker._movies_col")
@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
def test_step_prepare_single_name(mock_log, mock_update, mock_movies):
    """Prepare step stores target_path and target_paths for single name."""
    from app.modules.storage.tasks.worker import _step_prepare

    mock_movies.return_value.find_one.return_value = {
        "_id": "507f1f77bcf86cd799439011",
        "magnet_url": "magnet:?xt=urn:btih:abc",
        "source_task_name": "taskA",
    }

    task = {
        "task_id": "t1",
        "movie_id": "507f1f77bcf86cd799439011",
        "movie_code": "ABC-001",
    }
    config = {"target_folder": "/Movies"}

    result = _step_prepare(task, config)

    assert result["target_path"] == "/Movies/taskA/ABC-001"
    assert result["target_paths"] == ["/Movies/taskA/ABC-001"]
    assert result["source_task_name"] == "taskA"


@patch("app.modules.storage.tasks.worker._movies_col")
@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
def test_step_prepare_list_names(mock_log, mock_update, mock_movies):
    """Prepare step stores target_path (last) and target_paths (all) for list."""
    from app.modules.storage.tasks.worker import _step_prepare

    mock_movies.return_value.find_one.return_value = {
        "_id": "507f1f77bcf86cd799439011",
        "magnet_url": "magnet:?xt=urn:btih:abc",
        "source_task_name": ["taskA", "taskB"],
    }

    task = {
        "task_id": "t2",
        "movie_id": "507f1f77bcf86cd799439011",
        "movie_code": "ABC-002",
    }
    config = {"target_folder": "/Movies"}

    result = _step_prepare(task, config)

    assert result["target_path"] == "/Movies/taskB/ABC-002"
    assert result["target_paths"] == ["/Movies/taskA/ABC-002", "/Movies/taskB/ABC-002"]
    assert result["source_task_name"] == ["taskA", "taskB"]


@patch("app.modules.storage.tasks.worker._movies_col")
@patch("app.modules.storage.tasks.worker._update_task")
@patch("app.modules.storage.tasks.worker._append_log")
def test_step_prepare_stores_target_paths_in_update(mock_log, mock_update, mock_movies):
    """Prepare step passes target_paths to _update_task."""
    from app.modules.storage.tasks.worker import _step_prepare

    mock_movies.return_value.find_one.return_value = {
        "_id": "507f1f77bcf86cd799439011",
        "magnet_url": "magnet:?xt=urn:btih:abc",
        "source_task_name": ["taskA", "taskB", "taskC"],
    }

    task = {
        "task_id": "t3",
        "movie_id": "507f1f77bcf86cd799439011",
        "movie_code": "XYZ-999",
    }
    config = {"target_folder": "/Movies"}

    _step_prepare(task, config)

    # Verify _update_task was called with target_paths
    call_args = mock_update.call_args
    update_dict = call_args[0][1]  # positional args: (task_id, update_dict)
    assert "target_paths" in update_dict
    assert update_dict["target_paths"] == [
        "/Movies/taskA/XYZ-999",
        "/Movies/taskB/XYZ-999",
        "/Movies/taskC/XYZ-999",
    ]
    assert update_dict["target_path"] == "/Movies/taskC/XYZ-999"
