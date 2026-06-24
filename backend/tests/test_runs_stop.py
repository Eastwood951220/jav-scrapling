from unittest.mock import patch

from fastapi.testclient import TestClient

VALID_RUN_ID = "aaaaaaaaaaaaaaaaaaaaaaaa"


def test_stop_endpoint_returns_success_when_task_running():
    from app.main import app

    client = TestClient(app)
    with patch("app.api.runs.stop_current_task", return_value=True), \
         patch("app.api.runs.get_queue_status", return_value={"current_run_id": VALID_RUN_ID}):
        response = client.post(f"/api/runs/{VALID_RUN_ID}/stop")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_stop_endpoint_returns_400_when_no_task_running():
    from app.main import app

    client = TestClient(app)
    with patch("app.api.runs.stop_current_task", return_value=False):
        response = client.post(f"/api/runs/{VALID_RUN_ID}/stop")
    assert response.status_code == 400
