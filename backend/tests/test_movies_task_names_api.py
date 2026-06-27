from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def _make_app():
    from fastapi import FastAPI
    from app.modules.content.movies.router import router
    app = FastAPI()
    app.include_router(router)
    return app


def test_list_task_names_returns_sorted_unique_names():
    """GET /api/movies/task-names returns sorted unique source_task_name values."""
    mock_db = MagicMock()
    mock_col = MagicMock()
    # distinct() returns flat values from list fields, may include empties/dupes
    mock_col.distinct.return_value = ["TaskB", "", "TaskA", "TaskB", None]
    mock_db.__getitem__ = MagicMock(return_value=mock_col)

    with patch("app.modules.content.movies.router.get_mongo_db", return_value=mock_db):
        client = TestClient(_make_app())
        resp = client.get("/api/movies/task-names")

    assert resp.status_code == 200
    assert resp.json() == [{"name": "TaskA"}, {"name": "TaskB"}]


def test_list_task_names_returns_empty_when_no_movies():
    """GET /api/movies/task-names returns empty list when no movies exist."""
    mock_db = MagicMock()
    mock_col = MagicMock()
    mock_col.distinct.return_value = []
    mock_db.__getitem__ = MagicMock(return_value=mock_col)

    with patch("app.modules.content.movies.router.get_mongo_db", return_value=mock_db):
        client = TestClient(_make_app())
        resp = client.get("/api/movies/task-names")

    assert resp.status_code == 200
    assert resp.json() == []
