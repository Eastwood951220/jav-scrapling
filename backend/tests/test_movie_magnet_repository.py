from bson import ObjectId

from scraper.database.repositories.movie_magnet_repository import (
    MovieMagnetRepository,
    build_magnet_dedupe_key,
    extract_info_hash,
)


class FakeCollection:
    def __init__(self):
        self.indexes = []
        self.updates = []

    def create_indexes(self, indexes):
        self.indexes.extend(indexes)

    def update_one(self, query, update, upsert=False):
        self.updates.append((query, update, upsert))


class FakeDb:
    def __init__(self):
        self.collection = FakeCollection()

    def __getitem__(self, name):
        return self.collection


def test_extract_info_hash_lowercases_btih_value():
    assert (
        extract_info_hash("magnet:?xt=urn:btih:ABCDEF123456&dn=name")
        == "abcdef123456"
    )


def test_build_magnet_dedupe_key_uses_info_hash_when_present():
    dedupe_key = build_magnet_dedupe_key(
        "507f1f77bcf86cd799439011",
        {"magnet": "magnet:?xt=urn:btih:ABCDEF123456&dn=name"},
    )

    assert dedupe_key == "abcdef123456"


def test_build_magnet_dedupe_key_hashes_metadata_only_rows_deterministically():
    movie_id = "507f1f77bcf86cd799439011"
    magnet = {
        "name": "SSIS-889",
        "size_text": "2.75GB",
        "file_count": 20,
        "file_text": "20個文件",
        "date": "2023-10-17",
    }

    dedupe_key = build_magnet_dedupe_key(movie_id, magnet)

    assert dedupe_key == build_magnet_dedupe_key(movie_id, dict(magnet))
    assert len(dedupe_key) == 40


def test_upsert_many_normalizes_upserts_and_skips_empty_rows():
    fake = FakeDb()
    repository = MovieMagnetRepository(db=fake)
    movie_id = ObjectId("507f1f77bcf86cd799439011")
    movie = {
        "code": "SSIS-889",
        "title": "SSIS-889 Title",
        "source_url": "https://javdb.com/v/abc",
        "source_task_name": "javdb-daily",
    }
    magnets = [
        {
            "magnet": "magnet:?xt=urn:btih:ABCDEF123456&dn=name",
            "name": "SSIS-889-C.torrent",
            "size": 8960.0,
            "size_text": "8.75GB",
            "file_count": 1,
            "file_text": "1個文件",
            "tags": ["高清", "字幕"],
            "has_chinese_sub": True,
            "date": "2023-10-01",
        },
        {
            "magnet": "",
            "name": "",
            "size_text": "",
            "file_text": "",
        },
    ]

    saved = repository.upsert_many(movie_id, movie, magnets)

    assert saved == 1
    assert len(fake.collection.updates) == 1
    query, update, upsert = fake.collection.updates[0]
    assert query == {
        "movie_id": "507f1f77bcf86cd799439011",
        "dedupe_key": "abcdef123456",
    }
    assert upsert is True
    set_doc = update["$set"]
    assert set_doc["movie_code"] == "SSIS-889"
    assert set_doc["movie_title"] == "SSIS-889 Title"
    assert set_doc["magnet"] == "magnet:?xt=urn:btih:ABCDEF123456&dn=name"
    assert set_doc["info_hash"] == "abcdef123456"
    assert set_doc["size"] == 8960.0
    assert set_doc["size_text"] == "8.75GB"
    assert set_doc["file_count"] == 1
    assert set_doc["tags"] == ["高清", "字幕"]
    assert "created_at" in update["$setOnInsert"]
