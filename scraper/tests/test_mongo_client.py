from unittest.mock import MagicMock

from scraper.database import mongo_client
from scraper.database.indexes import ensure_indexes


class FakeAdmin:
    def __init__(self):
        self.commands = []

    def command(self, name):
        self.commands.append(name)
        return {"ok": 1}


class FakeClient:
    def __init__(self, uri, serverSelectionTimeoutMS):
        self.uri = uri
        self.serverSelectionTimeoutMS = serverSelectionTimeoutMS
        self.admin = FakeAdmin()
        self.closed = False

    def __getitem__(self, name):
        return {"name": name}

    def close(self):
        self.closed = True


def test_connect_mongo_pings_and_reuses_client(monkeypatch):
    created = []

    def fake_mongo_client(uri, serverSelectionTimeoutMS):
        client = FakeClient(uri, serverSelectionTimeoutMS)
        created.append(client)
        return client

    monkeypatch.setattr(mongo_client, "_client", None)
    monkeypatch.setattr(mongo_client, "MongoClient", fake_mongo_client)

    client = mongo_client.connect_mongo()
    reused = mongo_client.connect_mongo()

    assert client is reused
    assert len(created) == 1
    assert client.admin.commands == ["ping"]

    mongo_client.close_mongo()

    assert client.closed is True
    assert mongo_client._client is None


def test_ensure_indexes_does_not_send_background_command_option():
    db = MagicMock()
    collection = MagicMock()
    db.__getitem__.return_value = collection

    ensure_indexes(db, collection_name="movies")

    collection.create_indexes.assert_called_once()
    _, kwargs = collection.create_indexes.call_args
    assert "background" not in kwargs
