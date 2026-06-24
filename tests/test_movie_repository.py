from database.repositories.movie_repository import MovieRepository


class FakeInsertResult:
    inserted_id = "new-id"


class FakeCollection:
    def __init__(self):
        self.indexes = []
        self.documents = []
        self.queries = []

    def create_index(self, fields, unique=False, sparse=False):
        self.indexes.append((fields, unique, sparse))

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


def test_repository_inserts_into_task_collection(monkeypatch):
    fake_db = FakeDb()
    monkeypatch.setattr("database.repositories.movie_repository.get_mongo_db", lambda: fake_db)

    repository = MovieRepository()
    result = repository.upsert_movie(
        {
            "config_task_name": "Task.Name $1",
            "code": "ABC-001",
            "title": "Title",
        }
    )

    collection = fake_db.collections["Task_Name__1"]

    assert result == "new-id"
    assert collection.indexes == [([("code", 1)], True, True)]
    assert collection.queries == [{"code": "ABC-001"}]
    assert collection.documents[0]["code"] == "ABC-001"
    assert "created_at" in collection.documents[0]
    assert "updated_at" in collection.documents[0]
