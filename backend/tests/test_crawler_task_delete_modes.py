from unittest.mock import patch, MagicMock
from bson import ObjectId


def test_delete_normal_mode_removes_source_task_name():
    """Normal delete removes task name from movies.source_task_name arrays."""
    from fastapi.testclient import TestClient
    from app.main import app

    task_id = str(ObjectId())
    task_name = "test-task"

    mock_db = MagicMock()
    tasks_col = MagicMock()
    runs_col = MagicMock()
    movies_col = MagicMock()

    task_doc = {"_id": ObjectId(task_id), "name": task_name}
    tasks_col.find_one.return_value = task_doc
    runs_col.find_one.return_value = None  # no active runs
    runs_col.find.return_value = []  # no run history
    movies_col.update_many.return_value = MagicMock(modified_count=3)

    def get_collection(name):
        return {"crawl_tasks": tasks_col, "crawl_runs": runs_col, "movies": movies_col}.get(name, MagicMock())

    mock_db.__getitem__ = lambda self, key: get_collection(key)

    with patch("app.modules.crawler.tasks.router.get_database", return_value=mock_db):
        client = TestClient(app)
        resp = client.delete(f"/api/crawler/tasks/{task_id}?mode=normal")

    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] is True
    assert data["mode"] == "normal"
    # Should have called $pull on movies
    movies_col.update_many.assert_called_once()
    call_args = movies_col.update_many.call_args
    assert "$pull" in call_args[0][1]


def test_delete_complete_mode_deletes_movies_and_magnets():
    """Complete delete removes movies and magnets where source_task_name matches."""
    from fastapi.testclient import TestClient
    from app.main import app

    task_id = str(ObjectId())
    task_name = "test-task"

    mock_db = MagicMock()
    tasks_col = MagicMock()
    runs_col = MagicMock()
    movies_col = MagicMock()
    magnets_col = MagicMock()

    task_doc = {"_id": ObjectId(task_id), "name": task_name}
    tasks_col.find_one.return_value = task_doc
    runs_col.find_one.return_value = None
    runs_col.find.return_value = []

    # Movies to be deleted
    movie1_id = str(ObjectId())
    movie2_id = str(ObjectId())
    movies_col.find.return_value = [
        {"_id": ObjectId(movie1_id)},
        {"_id": ObjectId(movie2_id)},
    ]
    movies_col.delete_many.return_value = MagicMock(deleted_count=2)
    magnets_col.delete_many.return_value = MagicMock(deleted_count=5)

    def get_collection(name):
        return {
            "crawl_tasks": tasks_col,
            "crawl_runs": runs_col,
            "movies": movies_col,
            "movie_magnets": magnets_col,
        }.get(name, MagicMock())

    mock_db.__getitem__ = lambda self, key: get_collection(key)

    with patch("app.modules.crawler.tasks.router.get_database", return_value=mock_db):
        client = TestClient(app)
        resp = client.delete(f"/api/crawler/tasks/{task_id}?mode=complete")

    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] is True
    assert data["mode"] == "complete"
    assert data["movies_affected"] == 2
    # Should delete movies
    movies_col.delete_many.assert_called_once()
    # Should delete magnets
    magnets_col.delete_many.assert_called_once()


def test_delete_default_mode_is_normal():
    """Default mode (no query param) is normal."""
    from fastapi.testclient import TestClient
    from app.main import app

    task_id = str(ObjectId())
    mock_db = MagicMock()
    tasks_col = MagicMock()
    runs_col = MagicMock()
    movies_col = MagicMock()

    tasks_col.find_one.return_value = {"_id": ObjectId(task_id), "name": "t"}
    runs_col.find_one.return_value = None
    runs_col.find.return_value = []
    movies_col.update_many.return_value = MagicMock(modified_count=0)

    def get_collection(name):
        return {"crawl_tasks": tasks_col, "crawl_runs": runs_col, "movies": movies_col}.get(name, MagicMock())

    mock_db.__getitem__ = lambda self, key: get_collection(key)

    with patch("app.modules.crawler.tasks.router.get_database", return_value=mock_db):
        client = TestClient(app)
        resp = client.delete(f"/api/crawler/tasks/{task_id}")

    assert resp.status_code == 200
    assert resp.json()["mode"] == "normal"


def test_delete_invalid_mode_returns_400():
    """Invalid mode value returns 400."""
    from fastapi.testclient import TestClient
    from app.main import app

    task_id = str(ObjectId())
    mock_db = MagicMock()
    tasks_col = MagicMock()

    tasks_col.find_one.return_value = {"_id": ObjectId(task_id), "name": "t"}

    mock_db.__getitem__ = lambda self, key: tasks_col if key == "crawl_tasks" else MagicMock()

    with patch("app.modules.crawler.tasks.router.get_database", return_value=mock_db):
        client = TestClient(app)
        resp = client.delete(f"/api/crawler/tasks/{task_id}?mode=invalid")

    assert resp.status_code == 400
    assert "mode" in resp.json()["detail"].lower()


def test_delete_normal_mode_no_pull_when_no_task_name():
    """Normal mode skips $pull when task has no name."""
    from fastapi.testclient import TestClient
    from app.main import app

    task_id = str(ObjectId())
    mock_db = MagicMock()
    tasks_col = MagicMock()
    runs_col = MagicMock()
    movies_col = MagicMock()

    tasks_col.find_one.return_value = {"_id": ObjectId(task_id), "name": ""}
    runs_col.find_one.return_value = None
    runs_col.find.return_value = []

    def get_collection(name):
        return {"crawl_tasks": tasks_col, "crawl_runs": runs_col, "movies": movies_col}.get(name, MagicMock())

    mock_db.__getitem__ = lambda self, key: get_collection(key)

    with patch("app.modules.crawler.tasks.router.get_database", return_value=mock_db):
        client = TestClient(app)
        resp = client.delete(f"/api/crawler/tasks/{task_id}?mode=normal")

    assert resp.status_code == 200
    assert resp.json()["movies_affected"] == 0
    movies_col.update_many.assert_not_called()
