from fastapi.testclient import TestClient


def test_get_settings(client: TestClient):
    response = client.get("/api/settings")

    assert response.status_code == 200
    data = response.json()
    assert "mongo_uri" in data or "MONGO_URI" in data
    assert "max_list_pages" in data or "MAX_LIST_PAGES" in data


def test_update_settings(client: TestClient):
    payload = {"MAX_LIST_PAGES": 30, "LIST_PAGE_DELAY_MIN": 3.0}
    response = client.put("/api/settings", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["MAX_LIST_PAGES"] == 30
    assert data["LIST_PAGE_DELAY_MIN"] == 3.0
