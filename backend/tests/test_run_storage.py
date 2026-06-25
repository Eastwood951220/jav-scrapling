import json
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def tmp_run_dir(tmp_path):
    """Patch RUN_DATA_DIR to a temporary directory."""
    with patch("backend.app.run_storage.RUN_DATA_DIR", tmp_path):
        yield tmp_path


class TestSaveLogs:
    def test_creates_file_and_writes_json(self, tmp_run_dir):
        from backend.app.run_storage import save_logs

        logs = [
            {"timestamp": "2026-01-01T00:00:00Z", "level": "INFO", "message": "start"},
            {"timestamp": "2026-01-01T00:01:00Z", "level": "ERROR", "message": "fail"},
        ]
        save_logs("run_abc", logs)

        file = tmp_run_dir / "run_abc" / "logs.json"
        assert file.exists()
        data = json.loads(file.read_text(encoding="utf-8"))
        assert len(data) == 2
        assert data[0]["message"] == "start"
        assert data[1]["level"] == "ERROR"

    def test_overwrites_existing_file(self, tmp_run_dir):
        from backend.app.run_storage import save_logs

        save_logs("run_abc", [{"message": "old"}])
        save_logs("run_abc", [{"message": "new"}])

        data = json.loads((tmp_run_dir / "run_abc" / "logs.json").read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["message"] == "new"

    def test_creates_parent_directories(self, tmp_run_dir):
        from backend.app.run_storage import save_logs

        save_logs("deep/nested/run", [{"message": "ok"}])
        assert (tmp_run_dir / "deep" / "nested" / "run" / "logs.json").exists()


class TestLoadLogs:
    def test_returns_empty_list_when_file_missing(self, tmp_run_dir):
        from backend.app.run_storage import load_logs

        assert load_logs("nonexistent") == []

    def test_returns_saved_logs(self, tmp_run_dir):
        from backend.app.run_storage import save_logs, load_logs

        logs = [{"message": "hello"}, {"message": "world"}]
        save_logs("run_xyz", logs)
        assert load_logs("run_xyz") == logs


class TestSaveResult:
    def test_creates_file_and_writes_json(self, tmp_run_dir):
        from backend.app.run_storage import save_result

        result = {"total_tasks": 10, "saved": 8, "items": [{"code": "A"}]}
        save_result("run_abc", result)

        file = tmp_run_dir / "run_abc" / "result.json"
        assert file.exists()
        data = json.loads(file.read_text(encoding="utf-8"))
        assert data["total_tasks"] == 10
        assert data["items"] == [{"code": "A"}]


class TestLoadResult:
    def test_returns_none_when_file_missing(self, tmp_run_dir):
        from backend.app.run_storage import load_result

        assert load_result("nonexistent") is None

    def test_returns_saved_result(self, tmp_run_dir):
        from backend.app.run_storage import save_result, load_result

        result = {"total_tasks": 5, "items": []}
        save_result("run_def", result)
        assert load_result("run_def") == result


class TestGetResultSummary:
    def test_removes_items_key(self):
        from backend.app.run_storage import get_result_summary

        result = {"total_tasks": 10, "saved": 8, "items": [{"code": "A"}, {"code": "B"}]}
        summary = get_result_summary(result)
        assert "items" not in summary
        assert summary["total_tasks"] == 10
        assert summary["saved"] == 8

    def test_returns_copy_not_mutated(self):
        from backend.app.run_storage import get_result_summary

        result = {"total_tasks": 10, "items": [{"code": "A"}]}
        summary = get_result_summary(result)
        assert "items" in result  # original unchanged

    def test_handles_result_without_items(self):
        from backend.app.run_storage import get_result_summary

        result = {"total_tasks": 5, "saved": 3}
        summary = get_result_summary(result)
        assert summary == result

    def test_handles_none_input(self):
        from backend.app.run_storage import get_result_summary

        assert get_result_summary(None) is None
