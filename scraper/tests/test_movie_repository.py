from unittest.mock import MagicMock, patch

from scraper.database.repositories.movie_repository import MovieRepository


class FakeInsertResult:
    inserted_id = "new-id"


class FakeCollection:
    def __init__(self):
        self.indexes = []
        self.documents = []
        self.queries = []

    def create_indexes(self, indexes, background=False):
        self.background = background
        for idx in indexes:
            self.indexes.append(idx)

    def find_one(self, query):
        self.queries.append(query)
        return None

    def insert_one(self, document):
        self.documents.append(document)
        return FakeInsertResult()


class FakeDb:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        self.collections.setdefault(name, FakeCollection())
        return self.collections[name]


def test_repository_inserts_into_unified_movies_collection(monkeypatch):
    fake_db = FakeDb()
    monkeypatch.setattr(
        "scraper.database.repositories.movie_repository.get_mongo_db",
        lambda: fake_db,
    )
    monkeypatch.setattr(
        "scraper.database.repositories.movie_repository.ensure_indexes",
        lambda db, name: None,
    )

    repository = MovieRepository()
    result = repository.upsert_movie(
        {
            "source_task_name": "Task.Name $1",
            "code": "ABC-001",
            "source_name": "Title",
        }
    )

    collection = fake_db.collections["movies"]

    assert result == "new-id"
    assert collection.queries == [{"code": "ABC-001"}]
    assert collection.documents[0]["code"] == "ABC-001"
    assert collection.documents[0]["source_task_name"] == "Task.Name $1"
    assert "created_at" in collection.documents[0]
    assert "updated_at" in collection.documents[0]
