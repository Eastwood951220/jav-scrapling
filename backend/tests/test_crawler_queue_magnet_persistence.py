from bson import ObjectId

from app.modules.crawler.runs.queue import _persist_crawled_item


class FakeMovieRepository:
    def __init__(self):
        self.saved = []
        self.movie_id = ObjectId("507f1f77bcf86cd799439011")

    def upsert_movie(self, item):
        self.saved.append(item)
        return self.movie_id


class FakeMagnetRepository:
    def __init__(self):
        self.saved = []
        self.auto_selected = []

    def upsert_many(self, movie_id, movie, magnets):
        self.saved.append((movie_id, movie, magnets))
        return len(magnets)

    def auto_select_best_magnet(self, movie_id):
        self.auto_selected.append(movie_id)
        return None


def test_persist_crawled_item_removes_magnets_from_movie_and_saves_magnet_rows():
    movie_repo = FakeMovieRepository()
    magnet_repo = FakeMagnetRepository()
    cleaned_item = {
        "code": "SSIS-889",
        "title": "SSIS-889 Title",
        "source_url": "https://javdb.com/v/abc",
        "source_task_name": "task-a",
        "magnets": [
            {
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
        ],
    }

    movie_id = _persist_crawled_item(movie_repo, magnet_repo, cleaned_item)

    assert movie_id == ObjectId("507f1f77bcf86cd799439011")
    assert movie_repo.saved == [
        {
            "code": "SSIS-889",
            "title": "SSIS-889 Title",
            "source_url": "https://javdb.com/v/abc",
            "source_task_name": "task-a",
        }
    ]
    assert magnet_repo.saved == [
        (
            ObjectId("507f1f77bcf86cd799439011"),
            {
                "code": "SSIS-889",
                "title": "SSIS-889 Title",
                "source_url": "https://javdb.com/v/abc",
                "source_task_name": "task-a",
            },
            cleaned_item["magnets"],
        )
    ]
    assert "magnets" in cleaned_item


def test_persist_crawled_item_handles_items_without_magnets():
    movie_repo = FakeMovieRepository()
    magnet_repo = FakeMagnetRepository()

    movie_id = _persist_crawled_item(movie_repo, magnet_repo, {"code": "SSIS-001"})

    assert movie_id == ObjectId("507f1f77bcf86cd799439011")
    assert movie_repo.saved == [{"code": "SSIS-001"}]
    assert magnet_repo.saved == []
