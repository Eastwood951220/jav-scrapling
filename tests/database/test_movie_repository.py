"""Tests for MovieRepository using unified 'movies' collection."""

from unittest.mock import MagicMock, patch

from scraper.database.repositories.movie_repository import MovieRepository


class TestUpsertMovieUsesUnifiedCollection:
    """Verify upsert_movie writes to 'movies' collection, not dynamic names."""

    def test_uses_movies_collection(self):
        """All documents go to the 'movies' collection regardless of task name."""
        fake_db = MagicMock()
        fake_collection = MagicMock()
        fake_db.__getitem__ = MagicMock(return_value=fake_collection)
        fake_collection.find_one.return_value = None
        fake_collection.insert_one.return_value = MagicMock(inserted_id="fake-id")

        with patch(
            "scraper.database.repositories.movie_repository.get_mongo_db",
            return_value=fake_db,
        ), patch(
            "scraper.database.repositories.movie_repository.ensure_indexes",
        ):
            repo = MovieRepository()
            repo.upsert_movie(
                {
                    "code": "ABC-001",
                    "source_task_name": "Some Task",
                    "title": "Test",
                }
            )

        fake_db.__getitem__.assert_called_with("movies")

    def test_ignores_config_task_name_for_collection(self):
        """config_task_name does NOT determine the collection name."""
        fake_db = MagicMock()
        fake_collection = MagicMock()
        fake_db.__getitem__ = MagicMock(return_value=fake_collection)
        fake_collection.find_one.return_value = None
        fake_collection.insert_one.return_value = MagicMock(inserted_id="fake-id")

        with patch(
            "scraper.database.repositories.movie_repository.get_mongo_db",
            return_value=fake_db,
        ), patch(
            "scraper.database.repositories.movie_repository.ensure_indexes",
        ):
            repo = MovieRepository()
            repo.upsert_movie(
                {
                    "config_task_name": "Dynamic.Collection.Name",
                    "code": "XYZ-001",
                    "title": "Test",
                }
            )

        # Should always use "movies", never "Dynamic_Collection_Name"
        fake_db.__getitem__.assert_called_with("movies")


class TestUpsertMoviePreservesSourceTaskName:
    """Verify source_task_name field is preserved in stored documents."""

    def test_preserves_source_task_name(self):
        """source_task_name from item is stored as-is."""
        fake_db = MagicMock()
        fake_collection = MagicMock()
        fake_db.__getitem__ = MagicMock(return_value=fake_collection)
        fake_collection.find_one.return_value = None
        fake_collection.insert_one.return_value = MagicMock(inserted_id="fake-id")

        with patch(
            "scraper.database.repositories.movie_repository.get_mongo_db",
            return_value=fake_db,
        ), patch(
            "scraper.database.repositories.movie_repository.ensure_indexes",
        ):
            repo = MovieRepository()
            repo.upsert_movie(
                {
                    "code": "ABC-002",
                    "source_task_name": "My.Crawl.Task",
                    "title": "Test Movie",
                }
            )

        inserted_doc = fake_collection.insert_one.call_args[0][0]
        assert inserted_doc["source_task_name"] == "My.Crawl.Task"

    def test_source_task_name_none_when_absent(self):
        """Documents without source_task_name are inserted without it."""
        fake_db = MagicMock()
        fake_collection = MagicMock()
        fake_db.__getitem__ = MagicMock(return_value=fake_collection)
        fake_collection.find_one.return_value = None
        fake_collection.insert_one.return_value = MagicMock(inserted_id="fake-id")

        with patch(
            "scraper.database.repositories.movie_repository.get_mongo_db",
            return_value=fake_db,
        ), patch(
            "scraper.database.repositories.movie_repository.ensure_indexes",
        ):
            repo = MovieRepository()
            repo.upsert_movie(
                {
                    "code": "ABC-003",
                    "title": "No Task Name",
                }
            )

        inserted_doc = fake_collection.insert_one.call_args[0][0]
        assert "source_task_name" not in inserted_doc


class TestUpsertMovieSetsTimestamps:
    """Verify created_at and updated_at timestamps are set on insert."""

    def test_sets_created_at_and_updated_at(self):
        """Both timestamps are set when document is new."""
        fake_db = MagicMock()
        fake_collection = MagicMock()
        fake_db.__getitem__ = MagicMock(return_value=fake_collection)
        fake_collection.find_one.return_value = None
        fake_collection.insert_one.return_value = MagicMock(inserted_id="fake-id")

        with patch(
            "scraper.database.repositories.movie_repository.get_mongo_db",
            return_value=fake_db,
        ), patch(
            "scraper.database.repositories.movie_repository.ensure_indexes",
        ):
            repo = MovieRepository()
            result = repo.upsert_movie(
                {
                    "code": "ABC-004",
                    "title": "Timestamped Movie",
                }
            )

        assert result == "fake-id"
        inserted_doc = fake_collection.insert_one.call_args[0][0]
        assert "created_at" in inserted_doc
        assert "updated_at" in inserted_doc

    def test_does_not_overwrite_existing_timestamps(self):
        """Pre-existing timestamps in the document are preserved."""
        fake_db = MagicMock()
        fake_collection = MagicMock()
        fake_db.__getitem__ = MagicMock(return_value=fake_collection)
        fake_collection.find_one.return_value = None
        fake_collection.insert_one.return_value = MagicMock(inserted_id="fake-id")

        from datetime import datetime

        fixed_time = datetime(2025, 1, 1, 12, 0, 0)

        with patch(
            "scraper.database.repositories.movie_repository.get_mongo_db",
            return_value=fake_db,
        ), patch(
            "scraper.database.repositories.movie_repository.ensure_indexes",
        ):
            repo = MovieRepository()
            repo.upsert_movie(
                {
                    "code": "ABC-005",
                    "title": "Pre-timestamped",
                    "created_at": fixed_time,
                    "updated_at": fixed_time,
                }
            )

        inserted_doc = fake_collection.insert_one.call_args[0][0]
        assert inserted_doc["created_at"] == fixed_time
        assert inserted_doc["updated_at"] == fixed_time

    def test_returns_existing_id_when_already_exists(self):
        """Returns existing document's _id if already present."""
        fake_db = MagicMock()
        fake_collection = MagicMock()
        fake_db.__getitem__ = MagicMock(return_value=fake_collection)
        fake_collection.find_one.return_value = {"_id": "existing-id", "code": "ABC-006"}

        with patch(
            "scraper.database.repositories.movie_repository.get_mongo_db",
            return_value=fake_db,
        ), patch(
            "scraper.database.repositories.movie_repository.ensure_indexes",
        ):
            repo = MovieRepository()
            result = repo.upsert_movie(
                {
                    "code": "ABC-006",
                    "title": "Duplicate Movie",
                }
            )

        assert result == "existing-id"
        fake_collection.insert_one.assert_not_called()


class TestEnsureIndexesLazyInit:
    """Verify _ensure_indexes is called lazily on first use."""

    def test_ensure_indexes_called_once(self):
        """ensure_indexes is only called once across multiple operations."""
        fake_db = MagicMock()
        fake_collection = MagicMock()
        fake_db.__getitem__ = MagicMock(return_value=fake_collection)
        fake_collection.find_one.return_value = None
        fake_collection.insert_one.return_value = MagicMock(inserted_id="fake-id")

        mock_ensure = MagicMock()

        with patch(
            "scraper.database.repositories.movie_repository.get_mongo_db",
            return_value=fake_db,
        ), patch(
            "scraper.database.repositories.movie_repository.ensure_indexes",
            mock_ensure,
        ):
            repo = MovieRepository()
            repo.upsert_movie({"code": "A-001", "title": "First"})
            repo.upsert_movie({"code": "A-002", "title": "Second"})

        mock_ensure.assert_called_once_with(fake_db, "movies")
