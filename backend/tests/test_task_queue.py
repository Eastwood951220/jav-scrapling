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
