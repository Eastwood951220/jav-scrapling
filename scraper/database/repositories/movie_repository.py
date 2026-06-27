from datetime import datetime

from pymongo.errors import DuplicateKeyError, PyMongoError

from shared.database import get_database
from shared.database.collections import MOVIES
from scraper.config.logging import get_logger
from scraper.database.indexes import ensure_indexes
from shared.database.repositories.movie_repository import (
    MovieRepository as _SharedMovieRepository,
)


class MovieRepository(_SharedMovieRepository):
    COLLECTION_NAME = MOVIES

    def __init__(self):
        self.logger = get_logger("movie_repository")
        self.db = get_database()
        self.available = True
        self._indexes_ensured = False
        # Initialize shared repository with the same collection
        super().__init__(collection=self.db[self.COLLECTION_NAME])

    def _ensure_indexes(self) -> None:
        """Ensure indexes are created (lazy initialization)."""
        if not self._indexes_ensured:
            ensure_indexes(self.db, self.COLLECTION_NAME)
            self._indexes_ensured = True

    def get_collection(self):
        """Get the unified movies collection."""
        return self.collection

    def insert_if_not_exists(
        self,
        document: dict,
        unique_field: str = "code",
    ):
        if not self.available:
            return None

        try:
            self._ensure_indexes()
            collection = self.get_collection()

            existing = collection.find_one({unique_field: document.get(unique_field)})
            if existing:
                return existing["_id"]

            now = datetime.now()
            document.setdefault("created_at", now)
            document.setdefault("updated_at", now)

            result = collection.insert_one(document)
            return result.inserted_id
        except DuplicateKeyError:
            existing = self.get_collection().find_one(
                {unique_field: document.get(unique_field)}
            )
            return existing["_id"] if existing else None
        except PyMongoError as exc:
            self.available = False
            self.logger.warning("Failed to insert movie: %s", exc)
            return None

    def add_source_task_name(self, code: str, task_name: str) -> bool:
        """Add a task name to an existing movie's source_task_name list.
        Returns True if the movie was found and updated."""
        if not self.available or not code:
            return False

        try:
            collection = self.get_collection()
            result = collection.update_one(
                {"code": code},
                {
                    "$addToSet": {"source_task_name": task_name},
                    "$set": {"updated_at": datetime.now()},
                },
            )
            return result.modified_count > 0
        except PyMongoError as exc:
            self.logger.warning("Failed to add source_task_name: %s", exc)
            return False

    def upsert_movie(self, item: dict):
        if not self.available:
            return None

        code = item.get("code")
        unique_field = "code" if code else "source_url"

        return self.insert_if_not_exists(
            document=item,
            unique_field=unique_field,
        )
