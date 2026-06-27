from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def _make_app():
    from fastapi import FastAPI
    from app.modules.content.movies.router import router
    app = FastAPI()
    app.include_router(router)
    return app


def test_list_filters_returns_names_by_type():
    """GET /api/movies/filters?type=actor returns actor names."""
    mock_db = MagicMock()
    mock_col = MagicMock()
    mock_col.find.return_value.sort.return_value = [
        {"name": "Alice"},
        {"name": "Bob"},
    ]
    mock_db.__getitem__ = MagicMock(return_value=mock_col)

    with patch("app.modules.content.movies.router.get_mongo_db", return_value=mock_db):
        client = TestClient(_make_app())
        resp = client.get("/api/movies/filters", params={"type": "actor"})

    assert resp.status_code == 200
    assert resp.json() == ["Alice", "Bob"]


def test_list_filters_rejects_invalid_type():
    """GET /api/movies/filters?type=invalid returns 400."""
    client = TestClient(_make_app())
    resp = client.get("/api/movies/filters", params={"type": "invalid"})
    assert resp.status_code == 400
