"""Tests for storage_status filter on the movie list API."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_list_movies_storage_status_filter():
    """list_movies should filter by storage_status query param."""
    mock_db = MagicMock()
    movies_col = MagicMock()
    movies_col.count_documents.return_value = 0
    movies_col.find.return_value.sort.return_value.skip.return_value.limit.return_value = []
    magnets_col = MagicMock()

    def get_collection(name):
        if name == "movies":
            return movies_col
        if name == "movie_magnets":
            return magnets_col
        return MagicMock()

    mock_db.__getitem__ = lambda self, key: get_collection(key)

    with patch("app.modules.content.movies.router.get_database", return_value=mock_db):
        client = TestClient(app)
        resp = client.get("/api/movies?storage_status=completed")

    assert resp.status_code == 200
    # Verify the query included storage_summary.last_status
    call_args = movies_col.count_documents.call_args[0][0]
    assert call_args["storage_summary.last_status"] == "completed"
