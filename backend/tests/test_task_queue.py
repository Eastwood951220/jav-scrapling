import threading
from unittest.mock import MagicMock, patch

import pytest

from backend.app.task_queue import (
    _batch_save_items,
    _stop_event,
    enqueue_task,
    get_queue_status,
    stop_current_task,
)


class TestBatchSave:
    def test_batch_save_empty_items_returns_zero(self):
        repo = MagicMock()
        result = _batch_save_items([], 50, repo)
        assert result == 0
        repo.upsert_movie.assert_not_called()

    def test_batch_save_saves_all_items(self):
        repo = MagicMock()
        repo.upsert_movie.return_value = "some_id"
        items = [{"code": f"ABC-{i:03d}", "title": f"Title {i}"} for i in range(10)]
        result = _batch_save_items(items, 50, repo)
        assert result == 10
        assert repo.upsert_movie.call_count == 10

    def test_batch_save_logs_every_batch_size(self):
        repo = MagicMock()
        repo.upsert_movie.return_value = "some_id"
        items = [{"code": f"ABC-{i:03d}", "title": f"Title {i}"} for i in range(55)]
        with patch("builtins.print") as mock_print:
            result = _batch_save_items(items, 10, repo)
        assert result == 55
        # Should have printed batch progress at least 5 times (ceil(55/10) = 6 batches)
        assert mock_print.call_count >= 6


class TestStopSignal:
    def test_stop_event_starts_unset(self):
        _stop_event.clear()
        assert not _stop_event.is_set()

    def test_stop_current_task_sets_event(self):
        from backend.app.task_queue import _current_run_id

        _stop_event.clear()
        # Simulate a running task by setting _current_run_id
        import backend.app.task_queue as tq
        tq._current_run_id = "fake_run_id"
        try:
            result = stop_current_task()
            assert result is True
            assert _stop_event.is_set()
        finally:
            tq._current_run_id = None

    def test_get_queue_status_shows_stopped(self):
        _stop_event.clear()
        status = get_queue_status()
        assert "stop_requested" in status
        assert status["stop_requested"] is False

    def test_stop_current_task_returns_false_when_no_task_running(self):
        _stop_event.clear()
        # When _current_run_id is None, stop_current_task returns False
        # and does NOT set the stop event
        # We need to ensure no task is running
        from backend.app.task_queue import _current_run_id
        # _current_run_id should be None initially (no worker running)
        result = stop_current_task()
        assert result is False
        assert not _stop_event.is_set()


class TestCrashDrain:
    """Verify crash drain behavior: when crawl_javdb_task raises, already-
    collected items are persisted before the run is marked failed."""

    def test_batch_save_persists_all_items_on_drain(self):
        """_batch_save_items saves every item to the repository."""
        repo = MagicMock()

        saved_items = []

        def fake_upsert(item):
            saved_items.append(item)
            return f"id_{item['code']}"

        repo.upsert_movie.side_effect = fake_upsert

        # Simulate crash after collecting 25 items, draining in batches of 10
        items = [{"code": f"VID-{i:04d}", "title": f"Movie {i}"} for i in range(25)]
        saved = _batch_save_items(items, 10, repo)

        assert saved == 25
        assert len(saved_items) == 25
        assert saved_items[0]["code"] == "VID-0000"
        assert saved_items[-1]["code"] == "VID-0024"

    def test_batch_save_drain_handles_partial_repo_failure(self):
        """Items that fail to upsert are counted as not saved, others proceed."""
        repo = MagicMock()

        saved_codes = []

        def flaky_upsert(item):
            if item["code"] == "FAIL-0002":
                return None
            saved_codes.append(item["code"])
            return f"id_{item['code']}"

        repo.upsert_movie.side_effect = flaky_upsert

        items = [{"code": f"FAIL-{i:04d}"} for i in range(5)]
        saved = _batch_save_items(items, 50, repo)

        assert saved == 4
        assert "FAIL-0002" not in saved_codes
        assert len(saved_codes) == 4

    def test_drain_on_empty_items_is_noop(self):
        """Calling _batch_save_items with empty list returns 0 and no upsert."""
        repo = MagicMock()
        result = _batch_save_items([], 10, repo)
        assert result == 0
        repo.upsert_movie.assert_not_called()


class TestAppendLogToFile:
    """Verify _append_log writes to file instead of MongoDB $push."""

    def test_append_log_writes_to_file(self, tmp_path):
        from unittest.mock import patch as _patch

        from backend.app import task_queue as tq

        with _patch("app.run_storage.RUN_DATA_DIR", tmp_path):
            tq._append_log("test_run_001", "hello world", "INFO")

            from app.run_storage import load_logs
            logs = load_logs("test_run_001")
            assert len(logs) == 1
            assert logs[0]["message"] == "hello world"
            assert logs[0]["level"] == "INFO"

    def test_append_log_accumulates_entries(self, tmp_path):
        from unittest.mock import patch as _patch

        from backend.app import task_queue as tq

        with _patch("app.run_storage.RUN_DATA_DIR", tmp_path):
            tq._append_log("test_run_002", "first", "INFO")
            tq._append_log("test_run_002", "second", "WARNING")
            tq._append_log("test_run_002", "third", "ERROR")

            from app.run_storage import load_logs
            logs = load_logs("test_run_002")
            assert len(logs) == 3
            assert logs[0]["level"] == "INFO"
            assert logs[1]["level"] == "WARNING"
            assert logs[2]["level"] == "ERROR"
