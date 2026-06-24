from datetime import datetime

from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError, PyMongoError

from scraper.config.logging import get_logger
from scraper.database.mongo_client import get_mongo_db


class MovieRepository:
    def __init__(self):
        self.logger = get_logger("movie_repository")
        self.db = get_mongo_db()
        self.available = True

    def get_collection(self, name: str):
        safe_name = (name or "movies").replace(" ", "_").replace(".", "_").replace("$", "_")
        return self.db[safe_name]

    def insert_if_not_exists(
        self,
        collection_name: str,
        document: dict,
        unique_field: str = "code",
    ):
        if not self.available:
            return None

        try:
            collection = self.get_collection(collection_name)
            collection.create_index([(unique_field, ASCENDING)], unique=True, sparse=True)

            existing = collection.find_one({unique_field: document.get(unique_field)})
            if existing:
                return existing["_id"]

            now = datetime.now()
            document.setdefault("created_at", now)
            document.setdefault("updated_at", now)

            result = collection.insert_one(document)
            return result.inserted_id
        except DuplicateKeyError:
            existing = self.get_collection(collection_name).find_one(
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

        collection_name = item.get("config_task_name") or item.get("parent_task_name") or "movies"
        code = item.get("code")
        unique_field = "code" if code else "source_url"

        return self.insert_if_not_exists(
            collection_name=collection_name,
            document=item,
            unique_field=unique_field,
        )
