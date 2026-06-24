from unittest.mock import MagicMock, patch

from bson import ObjectId
from fastapi.testclient import TestClient


def test_list_collections(client: TestClient):
    mock_db = MagicMock()
    mock_db.list_collection_names.return_value = ["movies", "actors", "studios"]

    with patch("app.api.movies.get_mongo_db", return_value=mock_db):
        response = client.get("/api/movies/collections")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert "movies" in data
    # Excluded system collections should not appear
    assert "config_tasks" not in data
    assert "config_settings" not in data


def test_list_movies_empty(client: TestClient):
    mock_collection = MagicMock()
    mock_collection.count_documents.return_value = 0
    mock_collection.find.return_value.sort.return_value.skip.return_value.limit.return_value = []

    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    with patch("app.api.movies.get_mongo_db", return_value=mock_db):
        response = client.get("/api/movies")

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["limit"] == 20
    assert data["total_pages"] == 1


def test_list_movies_with_results(client: TestClient):
    fake_id = ObjectId()
    fake_movie = {"_id": fake_id, "title": "Test Movie", "code": "ABC-123", "created_at": "2024-01-01"}

    mock_collection = MagicMock()
    mock_collection.count_documents.return_value = 1
    mock_collection.find.return_value.sort.return_value.skip.return_value.limit.return_value = [fake_movie]

    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    with patch("app.api.movies.get_mongo_db", return_value=mock_db):
        response = client.get("/api/movies?page=1&limit=10")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Test Movie"
    assert data["items"][0]["_id"] == str(fake_id)
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["limit"] == 10


def test_list_movies_with_search(client: TestClient):
    mock_collection = MagicMock()
    mock_collection.count_documents.return_value = 1
    mock_collection.find.return_value.sort.return_value.skip.return_value.limit.return_value = []

    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    with patch("app.api.movies.get_mongo_db", return_value=mock_db):
        response = client.get("/api/movies?search=test&sort_by=title&sort_order=1")

    assert response.status_code == 200
    # Verify the search query was passed to count_documents and find
    query_arg = mock_collection.count_documents.call_args[0][0]
    assert "$or" in query_arg
    assert len(query_arg["$or"]) == 3
    assert query_arg["$or"][0]["title"]["$regex"] == "test"


def test_get_movie_found(client: TestClient):
    fake_id = ObjectId()
    fake_movie = {"_id": fake_id, "title": "Found Movie", "code": "XYZ-999"}

    mock_collection = MagicMock()
    mock_collection.find_one.return_value = fake_movie

    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    with patch("app.api.movies.get_mongo_db", return_value=mock_db):
        response = client.get(f"/api/movies/{fake_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Found Movie"
    assert data["_id"] == str(fake_id)


def test_get_movie_not_found(client: TestClient):
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = None

    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    fake_id = ObjectId()
    with patch("app.api.movies.get_mongo_db", return_value=mock_db):
        response = client.get(f"/api/movies/{fake_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"
