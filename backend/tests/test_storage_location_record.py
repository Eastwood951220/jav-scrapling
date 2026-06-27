"""Tests for storage location recording in _update_movie_summary."""

from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import pytest


def test_update_movie_summary_records_locations():
    """_update_movie_summary should include locations from moved_files."""
    from app.modules.storage.tasks.worker import _update_movie_summary

    mock_col = MagicMock()
    movie_id = "60f7c2d4e13823a3c8b45678"

    moved_files = [
        {
            "moved_path": "/Movies/taskA/ABC-001/ABC-001.mp4",
            "copied_paths": ["/Movies/taskB/ABC-001/ABC-001.mp4"],
        },
    ]

    with patch("app.modules.storage.tasks.worker._movies_col", return_value=mock_col):
        _update_movie_summary(movie_id, "T001", "completed", moved_files=moved_files)

    call_args = mock_col.update_one.call_args
    set_data = call_args[0][1]["$set"]
    assert "storage_summary.locations" in set_data
    locations = set_data["storage_summary.locations"]
    assert len(locations) == 2  # moved + copied
    assert locations[0]["path"] == "/Movies/taskA/ABC-001/ABC-001.mp4"
    assert locations[0]["target_folder"] == "/Movies/taskA/ABC-001"
    assert locations[1]["path"] == "/Movies/taskB/ABC-001/ABC-001.mp4"
    assert locations[1]["target_folder"] == "/Movies/taskB/ABC-001"


def test_update_movie_summary_no_locations_when_missing():
    """No locations recorded when moved_files is None."""
    from app.modules.storage.tasks.worker import _update_movie_summary

    mock_col = MagicMock()
    movie_id = "60f7c2d4e13823a3c8b45678"

    with patch("app.modules.storage.tasks.worker._movies_col", return_value=mock_col):
        _update_movie_summary(movie_id, "T001", "completed")

    call_args = mock_col.update_one.call_args
    set_data = call_args[0][1]["$set"]
    assert set_data["storage_summary.locations"] == []


def test_update_movie_summary_preserves_existing_fields():
    """Moved files should be stored alongside existing summary fields."""
    from app.modules.storage.tasks.worker import _update_movie_summary

    mock_col = MagicMock()
    movie_id = "60f7c2d4e13823a3c8b45678"

    moved_files = [
        {
            "moved_path": "/Movies/X/ABC-001.mp4",
            "copied_paths": [],
        },
    ]

    with patch("app.modules.storage.tasks.worker._movies_col", return_value=mock_col):
        _update_movie_summary(movie_id, "T001", "completed", moved_files=moved_files)

    set_data = mock_col.update_one.call_args[0][1]["$set"]
    assert set_data["storage_summary.last_task_id"] == "T001"
    assert set_data["storage_summary.last_status"] == "completed"
    assert "storage_summary.updated_at" in set_data
    assert len(set_data["storage_summary.locations"]) == 1


def test_update_movie_summary_multiple_files_with_multiple_copies():
    """Multiple files with multiple copies produce correct locations."""
    from app.modules.storage.tasks.worker import _update_movie_summary

    mock_col = MagicMock()
    movie_id = "60f7c2d4e13823a3c8b45678"

    moved_files = [
        {
            "moved_path": "/Movies/taskA/ABC-001/ABC-001-CD1.mp4",
            "copied_paths": [
                "/Movies/taskB/ABC-001/ABC-001-CD1.mp4",
                "/Movies/taskC/ABC-001/ABC-001-CD1.mp4",
            ],
        },
        {
            "moved_path": "/Movies/taskA/ABC-001/ABC-001-CD2.mp4",
            "copied_paths": [
                "/Movies/taskB/ABC-001/ABC-001-CD2.mp4",
            ],
        },
    ]

    with patch("app.modules.storage.tasks.worker._movies_col", return_value=mock_col):
        _update_movie_summary(movie_id, "T001", "completed", moved_files=moved_files)

    locations = mock_col.update_one.call_args[0][1]["$set"]["storage_summary.locations"]
    # 2 moved + 3 copied = 5 total
    assert len(locations) == 5
    paths = [loc["path"] for loc in locations]
    assert "/Movies/taskA/ABC-001/ABC-001-CD1.mp4" in paths
    assert "/Movies/taskB/ABC-001/ABC-001-CD1.mp4" in paths
    assert "/Movies/taskC/ABC-001/ABC-001-CD1.mp4" in paths
    assert "/Movies/taskA/ABC-001/ABC-001-CD2.mp4" in paths
    assert "/Movies/taskB/ABC-001/ABC-001-CD2.mp4" in paths


def test_update_movie_summary_non_completed_no_moved_files_skips_locations():
    """Non-completed status without moved_files should not set locations."""
    from app.modules.storage.tasks.worker import _update_movie_summary

    mock_col = MagicMock()
    movie_id = "60f7c2d4e13823a3c8b45678"

    with patch("app.modules.storage.tasks.worker._movies_col", return_value=mock_col):
        _update_movie_summary(movie_id, "T001", "running")

    set_data = mock_col.update_one.call_args[0][1]["$set"]
    assert "storage_summary.locations" not in set_data


def test_update_movie_summary_empty_moved_files_list():
    """Empty moved_files list should record empty locations."""
    from app.modules.storage.tasks.worker import _update_movie_summary

    mock_col = MagicMock()
    movie_id = "60f7c2d4e13823a3c8b45678"

    with patch("app.modules.storage.tasks.worker._movies_col", return_value=mock_col):
        _update_movie_summary(movie_id, "T001", "completed", moved_files=[])

    set_data = mock_col.update_one.call_args[0][1]["$set"]
    assert set_data["storage_summary.locations"] == []
