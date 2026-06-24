import importlib
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

# Ensure project root is on sys.path so config.settings can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set default environment variables for testing
_TEST_ENV_DEFAULTS = {
    "MONGO_URI": "mongodb://test:test@localhost:27017/",
    "MONGO_DB_NAME": "test_jav",
    "MONGO_CONNECT_TIMEOUT_MS": "5000",
    "MAX_LIST_PAGES": "10",
    "LIST_PAGE_DELAY_MIN": "1.0",
    "LIST_PAGE_DELAY_MAX": "2.0",
    "DETAIL_PAGE_DELAY_MIN": "0.5",
    "DETAIL_PAGE_DELAY_MAX": "1.0",
    "SECURITY_WAIT_SECONDS": "30",
    "REQUEST_TIMEOUT": "30",
    "USE_DYNAMIC_FETCHER": "false",
}
for _key, _value in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _value)


class InMemoryCursor:
    """Mock PyMongo cursor that supports .sort() chaining."""

    def __init__(self, docs: list[dict]):
        self._docs = docs

    def sort(self, key_or_list, direction=None):
        return self

    def __iter__(self):
        return iter(self._docs)


class InMemoryCollection:
    """A simple in-memory MongoDB collection mock that maintains state."""

    def __init__(self):
        self._docs: dict[str, dict] = {}

    def find(self, query=None):
        """Return a cursor-like object that supports .sort() and iteration."""
        docs = list(self._docs.values())
        return InMemoryCursor(docs)

    def find_one(self, query: dict | None = None):
        if query is None:
            return next(iter(self._docs.values()), None)
        if "_id" in query:
            oid = str(query["_id"])
            return self._docs.get(oid)
        # Simple field matching
        for doc in self._docs.values():
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None

    def insert_one(self, document: dict):
        oid = ObjectId()
        document["_id"] = oid
        self._docs[str(oid)] = document
        result = MagicMock()
        result.inserted_id = oid
        return result

    def find_one_and_update(self, query: dict, update: dict, return_document=True, **_kwargs):
        doc = self.find_one(query)
        if doc is None:
            return None
        set_fields = update.get("$set", update)
        for key, value in set_fields.items():
            if key != "_id":
                doc[key] = value
        return doc

    def delete_one(self, query: dict):
        doc = self.find_one(query)
        result = MagicMock()
        if doc is not None:
            oid = str(query["_id"])
            del self._docs[oid]
            result.deleted_count = 1
        else:
            result.deleted_count = 0
        return result


class InMemoryDB:
    """In-memory MongoDB database mock."""

    def __init__(self):
        self._collections: dict[str, InMemoryCollection] = {}

    def __getitem__(self, name: str) -> InMemoryCollection:
        if name not in self._collections:
            self._collections[name] = InMemoryCollection()
        return self._collections[name]


@pytest.fixture
def client():
    mock_db = InMemoryDB()

    # Patch get_mongo_db BEFORE importing app.main so that all modules
    # that import get_mongo_db get the patched version.
    with patch("database.mongo_client.get_mongo_db", return_value=mock_db), \
         patch("database.mongo_client.connect_mongo", return_value=MagicMock()), \
         patch("database.mongo_client.close_mongo", return_value=None):
        # Now import app.main — all its transitive imports will see the patched
        # database.mongo_client.get_mongo_db
        import app.main as main_module

        # Also patch start_scheduler on the freshly-loaded module
        with patch.object(main_module, "start_scheduler", return_value=None):
            with TestClient(main_module.app) as c:
                yield c

    # Clean up cached modules so each test gets a fresh import
    _cleanup_modules()


def _cleanup_modules():
    """Remove app modules from sys.modules so each test gets a fresh import."""
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("app.") or mod_name == "app":
            del sys.modules[mod_name]
