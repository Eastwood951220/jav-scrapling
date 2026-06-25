import time

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from scraper.config.logging import get_logger
from scraper.config.settings import MONGO_CONNECT_TIMEOUT_MS, MONGO_DB_NAME, MONGO_URI


_client: MongoClient | None = None
_logger = get_logger("mongo")

MAX_RETRIES = 10
RETRY_DELAY_SECONDS = 3


def connect_mongo() -> MongoClient:
    global _client

    if _client is not None:
        return _client

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=MONGO_CONNECT_TIMEOUT_MS,
            )
            _client.admin.command("ping")
            _logger.info("Connected to MongoDB: %s (attempt %d)", MONGO_DB_NAME, attempt)
            return _client
        except PyMongoError as e:
            _client = None
            last_error = e
            _logger.warning(
                "MongoDB connection attempt %d/%d failed: %s. Retrying in %ds...",
                attempt, MAX_RETRIES, e, RETRY_DELAY_SECONDS,
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    _logger.exception(
        "Failed to connect MongoDB after %d attempts: %s", MAX_RETRIES, MONGO_URI
    )
    raise ConnectionError(f"MongoDB unavailable after {MAX_RETRIES} retries") from last_error


def close_mongo() -> None:
    global _client

    if _client is None:
        return

    _client.close()
    _client = None
    _logger.info("MongoDB connection closed")


def get_mongo_db():
    client = connect_mongo()
    return client[MONGO_DB_NAME]


def sanitize_collection_name(name: str) -> str:
    """Sanitize a string for use as a MongoDB collection name."""
    return name.replace(" ", "_").replace(".", "_").replace("$", "_")
