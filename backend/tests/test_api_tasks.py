from fastapi.testclient import TestClient


def test_list_tasks_empty(client: TestClient):
    response = client.get("/api/tasks")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_create_task(client: TestClient):
    payload = {
        "name": "TestActor",
        "url": "https://javdb.com/actors/test123",
        "url_type": "actors",
        "is_skip": False,
        "max_list_pages": 5,
        "filter": {"only_chinese": False, "exclude_multi_person": True},
    }
    response = client.post("/api/tasks", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "TestActor"
    assert data["url_type"] == "actors"
    assert "_id" in data


def test_get_task(client: TestClient):
    payload = {"name": "GetTest", "url": "https://javdb.com/actors/abc", "url_type": "actors"}
    create_resp = client.post("/api/tasks", json=payload)
    task_id = create_resp.json()["_id"]

    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "GetTest"


def test_update_task(client: TestClient):
    payload = {"name": "UpdateTest", "url": "https://javdb.com/actors/xyz", "url_type": "actors"}
    create_resp = client.post("/api/tasks", json=payload)
    task_id = create_resp.json()["_id"]

    update_payload = {"name": "UpdatedName", "is_skip": True}
    response = client.put(f"/api/tasks/{task_id}", json=update_payload)
    assert response.status_code == 200
    assert response.json()["name"] == "UpdatedName"
    assert response.json()["is_skip"] is True


def test_delete_task(client: TestClient):
    payload = {"name": "DeleteTest", "url": "https://javdb.com/actors/del", "url_type": "actors"}
    create_resp = client.post("/api/tasks", json=payload)
    task_id = create_resp.json()["_id"]

    response = client.delete(f"/api/tasks/{task_id}")
    assert response.status_code == 200

    get_resp = client.get(f"/api/tasks/{task_id}")
    assert get_resp.status_code == 404


def test_get_task_invalid_id_returns_404(client: TestClient):
    response = client.get("/api/tasks/not-a-valid-objectid")
    assert response.status_code == 404


def test_get_task_nonexistent_id_returns_404(client: TestClient):
    response = client.get("/api/tasks/000000000000000000000000")
    assert response.status_code == 404


def test_delete_task_invalid_id_returns_404(client: TestClient):
    response = client.delete("/api/tasks/not-a-valid-objectid")
    assert response.status_code == 404


def test_create_task_invalid_body_returns_422(client: TestClient):
    response = client.post("/api/tasks", json={"name": "missing_url"})
    assert response.status_code == 422
