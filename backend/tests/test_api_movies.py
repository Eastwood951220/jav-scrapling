from unittest.mock import MagicMock, patch

from bson import ObjectId
from fastapi.testclient import TestClient


def test_list_collections(client: TestClient):
    """Verify list_collections returns the unified MOVIE_COLLECTION."""
    response = client.get("/api/movies/collections")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data == ["movies"]


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


def test_list_movies_filters_by_source_task_name(client: TestClient):
    """Verify that source_task_name parameter is passed as a query filter."""
    mock_collection = MagicMock()
    mock_collection.count_documents.return_value = 0
    mock_collection.find.return_value.sort.return_value.skip.return_value.limit.return_value = []

    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    with patch("app.api.movies.get_mongo_db", return_value=mock_db):
        response = client.get("/api/movies?source_task_name=my_task")

    assert response.status_code == 200

    # Verify source_task_name was included in the query
    query_arg = mock_collection.count_documents.call_args[0][0]
    assert "source_task_name" in query_arg
    assert query_arg["source_task_name"] == "my_task"


def test_list_movies_no_source_task_name_filter(client: TestClient):
    """Verify that omitting source_task_name does not add it to the query."""
    mock_collection = MagicMock()
    mock_collection.count_documents.return_value = 0
    mock_collection.find.return_value.sort.return_value.skip.return_value.limit.return_value = []

    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    with patch("app.api.movies.get_mongo_db", return_value=mock_db):
        response = client.get("/api/movies")

    assert response.status_code == 200

    query_arg = mock_collection.count_documents.call_args[0][0]
    assert "source_task_name" not in query_arg


def test_list_movies_uses_unified_collection(client: TestClient):
    """Verify list_movies always accesses the 'movies' collection, not a dynamic one."""
    mock_collection = MagicMock()
    mock_collection.count_documents.return_value = 0
    mock_collection.find.return_value.sort.return_value.skip.return_value.limit.return_value = []

    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    with patch("app.api.movies.get_mongo_db", return_value=mock_db):
        client.get("/api/movies")

    # Verify it accessed "movies" collection specifically
    mock_db.__getitem__.assert_called_with("movies")


def test_get_movie_uses_unified_collection(client: TestClient):
    """Verify get_movie always accesses the 'movies' collection."""
    fake_id = ObjectId()
    fake_movie = {"_id": fake_id, "title": "Test", "code": "X-1"}

    mock_collection = MagicMock()
    mock_collection.find_one.return_value = fake_movie

    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    with patch("app.api.movies.get_mongo_db", return_value=mock_db):
        client.get(f"/api/movies/{fake_id}")

    mock_db.__getitem__.assert_called_with("movies")


def test_delete_collection_blocks_movies(client: TestClient):
    """Verify that deleting the unified 'movies' collection is blocked."""
    mock_db = MagicMock()
    mock_db.list_collection_names.return_value = ["movies"]

    with patch("app.api.movies.get_mongo_db", return_value=mock_db):
        response = client.delete("/api/movies/collections/movies")

    assert response.status_code == 400
