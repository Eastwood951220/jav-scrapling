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
