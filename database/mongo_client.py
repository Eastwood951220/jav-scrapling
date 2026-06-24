from pymongo import MongoClient
from pymongo.errors import PyMongoError

from config.logging import get_logger
from config.settings import MONGO_CONNECT_TIMEOUT_MS, MONGO_DB_NAME, MONGO_URI


_client: MongoClient | None = None
_logger = get_logger("mongo")


def connect_mongo() -> MongoClient:
    global _client

    if _client is not None:
        return _client

    try:
        _client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=MONGO_CONNECT_TIMEOUT_MS,
        )
        _client.admin.command("ping")
        _logger.info("Connected to MongoDB: %s", MONGO_DB_NAME)
        return _client
    except PyMongoError:
        _client = None
        _logger.exception("Failed to connect MongoDB: %s", MONGO_URI)
        raise


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
