from unittest.mock import MagicMock, patch
from bson import ObjectId


def test_sync_location_checks_files_on_clouddrive():
    """sync-location should check each location on CloudDrive2 and update status."""
    from fastapi.testclient import TestClient
    from app.main import app

    movie_id = str(ObjectId())
    mock_db = MagicMock()
    movies_col = MagicMock()
    movies_col.find_one.return_value = {
        "_id": ObjectId(movie_id),
        "code": "ABC-001",
        "storage_summary": {
            "last_status": "completed",
            "locations": [
                {"path": "/Movies/taskA/ABC-001.mp4", "target_folder": "/Movies/taskA"},
                {"path": "/Movies/taskB/ABC-001.mp4", "target_folder": "/Movies/taskB"},
            ],
        },
    }

    mock_cd2 = MagicMock()
    # First location exists, second doesn't
    mock_file = MagicMock()
    mock_file.name = "ABC-001.mp4"
    mock_file.fullPathName = "/Movies/taskA/ABC-001.mp4"
    mock_file.size = 1024
    mock_file.isDirectory = False
    mock_cd2.find_file_by_path.side_effect = [mock_file, None]

    mock_config_col = MagicMock()
    mock_config_col.find_one.return_value = {"grpc_host": "localhost:19798", "api_token": ""}

    def get_collection(name):
        if name == "movies":
            return movies_col
        if name == "storage_config":
            return mock_config_col
        return MagicMock()

    mock_db.__getitem__ = lambda self, key: get_collection(key)

    with patch("app.modules.content.movies.router.get_mongo_db", return_value=mock_db), \
         patch("app.modules.content.movies.router._build_cd2_client", return_value=mock_cd2):
        client = TestClient(app)
        resp = client.post(f"/api/movies/{movie_id}/sync-location")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["locations"]) == 2
    assert data["locations"][0]["exists"] is True
    assert data["locations"][1]["exists"] is False
    assert data["synced"] is False  # not all exist


def test_sync_location_batch_checks_multiple_movies():
    """batch sync-location should check locations for multiple movies."""
    from fastapi.testclient import TestClient
    from app.main import app

    movie_id_1 = str(ObjectId())
    movie_id_2 = str(ObjectId())

    mock_db = MagicMock()
    movies_col = MagicMock()

    def find_one(query, *args, **kwargs):
        mid = query.get("_id")
        if mid == ObjectId(movie_id_1):
            return {
                "_id": ObjectId(movie_id_1),
                "code": "ABC-001",
                "storage_summary": {
                    "last_status": "pending",
                    "locations": [
                        {"path": "/Movies/ABC-001.mp4", "target_folder": "/Movies"},
                    ],
                },
            }
        if mid == ObjectId(movie_id_2):
            return {
                "_id": ObjectId(movie_id_2),
                "code": "DEF-002",
                "storage_summary": {
                    "last_status": "pending",
                    "locations": [
                        {"path": "/Movies/DEF-002.mp4", "target_folder": "/Movies"},
                    ],
                },
            }
        return None

    movies_col.find_one.side_effect = find_one

    mock_cd2 = MagicMock()
    # First movie's file exists, second doesn't
    mock_file = MagicMock()
    mock_file.name = "ABC-001.mp4"
    mock_cd2.find_file_by_path.side_effect = [mock_file, None]

    mock_config_col = MagicMock()
    mock_config_col.find_one.return_value = {"grpc_host": "localhost:19798", "api_token": ""}

    def get_collection(name):
        if name == "movies":
            return movies_col
        if name == "storage_config":
            return mock_config_col
        return MagicMock()

    mock_db.__getitem__ = lambda self, key: get_collection(key)

    with patch("app.modules.content.movies.router.get_mongo_db", return_value=mock_db), \
         patch("app.modules.content.movies.router._build_cd2_client", return_value=mock_cd2):
        client = TestClient(app)
        resp = client.post(
            "/api/movies/sync-location/batch",
            json={"ids": [movie_id_1, movie_id_2]},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["results"][0]["synced"] is True
    assert data["results"][0]["locations"][0]["exists"] is True
    assert data["results"][1]["synced"] is False
    assert data["results"][1]["locations"][0]["exists"] is False


def test_sync_location_no_locations_returns_empty():
    """sync-location should return empty when movie has no storage locations."""
    from fastapi.testclient import TestClient
    from app.main import app

    movie_id = str(ObjectId())
    mock_db = MagicMock()
    movies_col = MagicMock()
    movies_col.find_one.return_value = {
        "_id": ObjectId(movie_id),
        "code": "XYZ-999",
    }

    mock_cd2 = MagicMock()

    mock_config_col = MagicMock()
    mock_config_col.find_one.return_value = {"grpc_host": "localhost:19798", "api_token": ""}

    def get_collection(name):
        if name == "movies":
            return movies_col
        if name == "storage_config":
            return mock_config_col
        return MagicMock()

    mock_db.__getitem__ = lambda self, key: get_collection(key)

    with patch("app.modules.content.movies.router.get_mongo_db", return_value=mock_db), \
         patch("app.modules.content.movies.router._build_cd2_client", return_value=mock_cd2):
        client = TestClient(app)
        resp = client.post(f"/api/movies/{movie_id}/sync-location")

    assert resp.status_code == 200
    data = resp.json()
    assert data["locations"] == []
    assert data["synced"] is False
