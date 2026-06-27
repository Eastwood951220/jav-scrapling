from bson import ObjectId

from app.modules.content.movies.router import _attach_movie_magnets, _magnet_export_item


class FakeCursor(list):
    def sort(self, *args):
        return self


class FakeMagnetCollection:
    def __init__(self, docs):
        self.docs = docs
        self.last_query = None

    def find(self, query, projection=None):
        self.last_query = query
        movie_ids = set(query["movie_id"]["$in"])
        return FakeCursor([doc for doc in self.docs if doc["movie_id"] in movie_ids])


def test_attach_movie_magnets_groups_rows_by_movie_id():
    movie_id = ObjectId("507f1f77bcf86cd799439011")
    movies = [{"_id": movie_id, "code": "SSIS-889"}]
    magnets_col = FakeMagnetCollection(
        [
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),
                "movie_id": str(movie_id),
                "magnet": "magnet:?xt=urn:btih:abc123",
                "name": "SSIS-889",
                "size": 9431.04,
                "size_text": "9.21GB",
                "file_count": 1,
                "file_text": "1個文件",
                "tags": ["高清"],
                "has_chinese_sub": False,
                "date": "2023-09-22",
            }
        ]
    )

    _attach_movie_magnets(movies, magnets_col)

    assert movies[0]["magnets"] == [
        {
            "_id": "507f1f77bcf86cd799439012",
            "movie_id": str(movie_id),
            "magnet": "magnet:?xt=urn:btih:abc123",
            "name": "SSIS-889",
            "title": "SSIS-889",
            "size": "9.21GB",
            "size_mb": 9431.04,
            "size_text": "9.21GB",
            "file_count": 1,
            "file_text": "1個文件",
            "tags": ["高清"],
            "has_chinese_sub": False,
            "date": "2023-09-22",
            "dedupe_key": "",
            "weight": 0,
        }
    ]


def test_magnet_export_item_preserves_movie_and_magnet_fields():
    item = _magnet_export_item(
        {"code": "SSIS-889", "source_name": "Movie Title", "name": "Fallback"},
        {
            "magnet": "magnet:?xt=urn:btih:abc123",
            "name": "SSIS-889-C.torrent",
            "size_text": "8.75GB",
            "size": 8960.0,
        },
    )

    assert item == {
        "code": "SSIS-889",
        "title": "Movie Title",
        "magnet": "magnet:?xt=urn:btih:abc123",
        "name": "SSIS-889-C.torrent",
        "size": "8.75GB",
        "size_mb": 8960.0,
    }
