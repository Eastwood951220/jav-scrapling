from unittest.mock import patch

from fastapi.testclient import TestClient


def test_list_schedules_empty(client: TestClient):
    response = client.get("/api/schedules")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_schedule(client: TestClient):
    # Patch add_schedule_job to avoid APScheduler import during test
    with patch("app.api.schedules.add_schedule_job"):
        payload = {
            "name": "DailyCrawl",
            "task_ids": [],
            "cron_expression": "0 2 * * *",
            "enabled": True,
        }
        response = client.post("/api/schedules", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "DailyCrawl"
        assert data["cron_expression"] == "0 2 * * *"
        assert "_id" in data


def test_get_schedule(client: TestClient):
    with patch("app.api.schedules.add_schedule_job"):
        payload = {"name": "GetSchedule", "task_ids": [], "cron_expression": "0 3 * * *"}
        create_resp = client.post("/api/schedules", json=payload)
        schedule_id = create_resp.json()["_id"]

    response = client.get(f"/api/schedules/{schedule_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "GetSchedule"


def test_update_schedule(client: TestClient):
    with patch("app.api.schedules.add_schedule_job"), \
         patch("app.api.schedules.remove_schedule_job"):
        payload = {"name": "UpdateMe", "task_ids": [], "cron_expression": "0 4 * * *"}
        create_resp = client.post("/api/schedules", json=payload)
        schedule_id = create_resp.json()["_id"]

        update_payload = {"name": "UpdatedSchedule", "enabled": False}
        response = client.put(f"/api/schedules/{schedule_id}", json=update_payload)
        assert response.status_code == 200
        assert response.json()["name"] == "UpdatedSchedule"
        assert response.json()["enabled"] is False


def test_delete_schedule(client: TestClient):
    with patch("app.api.schedules.add_schedule_job"), \
         patch("app.api.schedules.remove_schedule_job"):
        payload = {"name": "DeleteMe", "task_ids": [], "cron_expression": "0 5 * * *"}
        create_resp = client.post("/api/schedules", json=payload)
        schedule_id = create_resp.json()["_id"]

        response = client.delete(f"/api/schedules/{schedule_id}")
        assert response.status_code == 200
        assert response.json() == {"deleted": True}

        get_resp = client.get(f"/api/schedules/{schedule_id}")
        assert get_resp.status_code == 404


def test_get_schedule_invalid_id_returns_400(client: TestClient):
    response = client.get("/api/schedules/not-a-valid-objectid")
    assert response.status_code == 400


def test_get_schedule_nonexistent_id_returns_404(client: TestClient):
    response = client.get("/api/schedules/000000000000000000000000")
    assert response.status_code == 404


def test_create_schedule_invalid_body_returns_422(client: TestClient):
    response = client.post("/api/schedules", json={"cron_expression": "bad"})
    assert response.status_code == 422


def test_create_schedule_invalid_cron_returns_422(client: TestClient):
    response = client.post("/api/schedules", json={
        "name": "BadCron",
        "cron_expression": "this is not a cron",
    })
    assert response.status_code == 422
