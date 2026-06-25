from datetime import datetime

from pymongo.errors import DuplicateKeyError, PyMongoError

from scraper.config.logging import get_logger
from scraper.database.indexes import ensure_indexes
from scraper.database.mongo_client import get_mongo_db


class MovieRepository:
    COLLECTION_NAME = "movies"

    def __init__(self):
        self.logger = get_logger("movie_repository")
        self.db = get_mongo_db()
        self.available = True
        self._indexes_ensured = False

    def _ensure_indexes(self) -> None:
        """Ensure indexes are created (lazy initialization)."""
        if not self._indexes_ensured:
            ensure_indexes(self.db, self.COLLECTION_NAME)
            self._indexes_ensured = True

    def get_collection(self):
        """Get the unified movies collection."""
        return self.db[self.COLLECTION_NAME]

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

    def upsert_movie(self, item: dict):
        if not self.available:
            return None

        code = item.get("code")
        unique_field = "code" if code else "source_url"

        return self.insert_if_not_exists(
            document=item,
            unique_field=unique_field,
        )
