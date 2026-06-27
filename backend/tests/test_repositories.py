from datetime import datetime, timezone
from unittest.mock import MagicMock


class FakeResult:
    def __init__(self, inserted_id=None, modified_count=1, deleted_count=1):
        self.inserted_id = inserted_id
        self.modified_count = modified_count
        self.deleted_count = deleted_count


class FakeCollection:
    def __init__(self):
        self.docs = []
        self.last_update = None
        self.find_one_and_update_calls = []

    def insert_one(self, document):
        stored = dict(document)
        stored.setdefault("_id", "generated-id")
        self.docs.append(stored)
        return FakeResult(inserted_id=stored["_id"])

    def find_one(self, query):
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in query.items() if not isinstance(value, dict)):
                return dict(doc)
        return None

    def update_one(self, query, update, upsert=False):
        self.last_update = (query, update, upsert)
        return FakeResult(modified_count=1)

    def find_one_and_update(self, query, update, sort=None):
        self.find_one_and_update_calls.append((query, update, sort))
        return self.docs[0] if self.docs else None


def test_storage_config_repository_preserves_existing_token_when_masked():
    from shared.database.repositories.storage_config_repository import StorageConfigRepository

    col = FakeCollection()
    col.docs.append({"_key": "default", "api_token": "real-token", "grpc_host": "localhost:9798"})
    repo = StorageConfigRepository(collection=col)

    saved = repo.save_default({"api_token": "************oken", "grpc_host": "http://host:9798"})

    assert saved["api_token"] == "real-token"
    assert col.last_update[0] == {"_key": "default"}
    assert col.last_update[2] is True


def test_storage_task_repository_find_next_executable_priority_query():
    from shared.database.repositories.storage_task_repository import StorageTaskRepository

    col = FakeCollection()
    col.docs.append({"task_id": "T001", "status": "pending"})
    repo = StorageTaskRepository(collection=col)

    result = repo.find_next_executable(datetime.now(timezone.utc))

    assert result["task_id"] == "T001"
    assert col.find_one_and_update_calls[0][0] == {"status": "running"}


def test_movie_repository_update_storage_summary_locations():
    from shared.database.repositories.movie_repository import MovieRepository

    col = FakeCollection()
    repo = MovieRepository(collection=col)

    repo.update_storage_summary(
        movie_id="60f7c2d4e13823a3c8b45678",
        task_id="T001",
        status="completed",
        final_files=[
            {"path": "/Movies/A/ABC-001.mp4", "target_folder": "/Movies/A"},
        ],
    )

    update = col.last_update[1]["$set"]
    assert update["storage_summary.last_task_id"] == "T001"
    assert update["storage_summary.last_status"] == "completed"
    assert update["storage_summary.locations"][0]["path"] == "/Movies/A/ABC-001.mp4"
