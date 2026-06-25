from backend.app.task_queue import (
    _stop_event,
    get_queue_status,
    stop_current_task,
)


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
