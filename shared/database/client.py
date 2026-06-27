from __future__ import annotations

import logging
import time

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from shared.database.config import DatabaseConfig, get_database_config

_client: MongoClient | None = None
_logger = logging.getLogger("mongo")


def connect_database(config: DatabaseConfig | None = None) -> MongoClient:
    global _client

    if _client is not None:
        return _client

    active_config = config or get_database_config()
    last_error: Exception | None = None

    for attempt in range(1, active_config.max_retries + 1):
        try:
            _client = MongoClient(
                active_config.mongo_uri,
                serverSelectionTimeoutMS=active_config.connect_timeout_ms,
            )
            _client.admin.command("ping")
            _logger.info(
                "Connected to MongoDB: %s (attempt %d)",
                active_config.database_name,
                attempt,
            )
            return _client
        except PyMongoError as exc:
            _client = None
            last_error = exc
            _logger.warning(
                "MongoDB connection attempt %d/%d failed: %s. Retrying in %ds...",
                attempt,
                active_config.max_retries,
                exc,
                active_config.retry_delay_seconds,
            )
            if attempt < active_config.max_retries:
                time.sleep(active_config.retry_delay_seconds)

    _logger.exception(
        "Failed to connect MongoDB after %d attempts: %s",
        active_config.max_retries,
        active_config.mongo_uri,
    )
    raise ConnectionError(
        f"MongoDB unavailable after {active_config.max_retries} retries"
    ) from last_error


def close_database() -> None:
    global _client

    if _client is None:
        return

    _client.close()
    _client = None
    _logger.info("MongoDB connection closed")


def get_database():
    client = connect_database()
    return client[get_database_config().database_name]


def database_health_check() -> bool:
    try:
        connect_database().admin.command("ping")
        return True
    except Exception:
        return False


def sanitize_collection_name(name: str) -> str:
    return name.replace(" ", "_").replace(".", "_").replace("$", "_")
