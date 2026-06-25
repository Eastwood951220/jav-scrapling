from unittest.mock import patch

from fastapi.testclient import TestClient


def test_list_runs_empty(client: TestClient):
    response = client.get("/api/runs")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["items"] == []


def test_get_queue_status(client: TestClient):
    response = client.get("/api/runs/queue-status")
    assert response.status_code == 200
    data = response.json()
    assert "queue_size" in data
    assert "is_running" in data
    assert "current_run_id" in data


def test_enqueue_task_creates_run(client: TestClient):
    with patch("backend.app.task_queue._worker_running", True):
        # Create a task via the API
        payload = {
            "name": "Test",
            "url": "https://javdb.com/actors/x",
            "url_type": "actors",
            "is_skip": False,
            "max_list_pages": 5,
            "filter": {"only_chinese": False, "exclude_multi_person": False},
        }
        create_resp = client.post("/api/tasks", json=payload)
        assert create_resp.status_code == 201
        task_id = create_resp.json()["_id"]

        # Enqueue
        response = client.post(f"/api/tasks/{task_id}/run")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "queued"
        assert data["task_id"] == task_id
        assert "_id" in data

        # List runs
        resp2 = client.get("/api/runs")
        assert resp2.status_code == 200
        assert len(resp2.json()["items"]) >= 1


def _create_run(client: TestClient) -> str:
    """Helper: create a task and enqueue a run, return the run_id."""
    payload = {
        "name": "Test",
        "url": "https://javdb.com/actors/x",
        "url_type": "actors",
        "is_skip": False,
        "max_list_pages": 5,
        "filter": {"only_chinese": False, "exclude_multi_person": False},
    }
    with patch("backend.app.task_queue._worker_running", True):
        create_resp = client.post("/api/tasks", json=payload)
        task_id = create_resp.json()["_id"]
        run_resp = client.post(f"/api/tasks/{task_id}/run")
        return run_resp.json()["_id"]


class TestListRunsLightweight:
    """Verify list endpoint returns lightweight documents."""

    def test_list_excludes_items_from_result(self, client: TestClient):
        from bson import ObjectId

        from scraper.database.mongo_client import get_mongo_db

        payload = {
            "name": "Test",
            "url": "https://javdb.com/actors/x",
            "url_type": "actors",
            "is_skip": False,
            "max_list_pages": 5,
            "filter": {"only_chinese": False, "exclude_multi_person": False},
        }
        with patch("backend.app.task_queue._worker_running", True):
            create_resp = client.post("/api/tasks", json=payload)
            task_id = create_resp.json()["_id"]
            run_resp = client.post(f"/api/tasks/{task_id}/run")
            run_id = run_resp.json()["_id"]

        # Manually set a result with items in MongoDB (simulating old data)
        get_mongo_db()["task_runs"].update_one(
            {"_id": ObjectId(run_id)},
            {"$set": {
                "status": "completed",
                "result": {
                    "total_tasks": 5,
                    "saved": 3,
                    "items": [{"code": "A"}, {"code": "B"}],
                },
                "logs": [
                    {"timestamp": "2026-01-01T00:00:00Z", "level": "INFO", "message": "log 1"},
                ],
            }},
        )

        resp = client.get("/api/runs")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1

        run = next(r for r in items if r["_id"] == run_id)
        # The list view should not include items in result
        if run.get("result"):
            assert "items" not in run["result"]
        # The list view should not include logs
        assert run.get("logs", []) == []


class TestRunDetailFromFiles:
    """Verify detail endpoint loads logs/result from files with MongoDB fallback."""

    def test_detail_loads_logs_from_file(self, client: TestClient):
        from backend.app.run_storage import save_logs

        run_id = _create_run(client)

        # Save logs to file
        logs = [
            {"timestamp": "2026-01-01T00:00:00Z", "level": "INFO", "message": "file log 1"},
            {"timestamp": "2026-01-01T00:01:00Z", "level": "ERROR", "message": "file log 2"},
        ]
        save_logs(run_id, logs)

        # Fetch detail — should return file-based logs
        resp = client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["logs"]) == 2
        assert data["logs"][0]["message"] == "file log 1"

    def test_detail_falls_back_to_mongodb_logs(self, client: TestClient):
        """When no log file exists, falls back to MongoDB logs (empty list)."""
        run_id = _create_run(client)

        # No file saved — should fall back to MongoDB logs (empty list)
        resp = client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200
        assert resp.json()["logs"] == []

    def test_detail_loads_result_from_file(self, client: TestClient):
        from backend.app.run_storage import save_result

        run_id = _create_run(client)

        # Save result to file
        result_data = {"total": 5, "items": [{"id": "abc"}, {"id": "def"}]}
        save_result(run_id, result_data)

        # Fetch detail — should return file-based result
        resp = client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["total"] == 5
        assert len(data["result"]["items"]) == 2

    def test_detail_falls_back_to_mongodb_result(self, client: TestClient):
        """When no result file exists, falls back to MongoDB result (None)."""
        run_id = _create_run(client)

        # No file saved — should fall back to MongoDB result (None)
        resp = client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200
        assert resp.json()["result"] is None
