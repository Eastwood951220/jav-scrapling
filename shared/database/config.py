from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseConfig:
    mongo_uri: str
    database_name: str
    connect_timeout_ms: int
    max_retries: int = 10
    retry_delay_seconds: int = 3


def get_database_config() -> DatabaseConfig:
    return DatabaseConfig(
        mongo_uri=os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/"),
        database_name=os.getenv("MONGO_DB_NAME", "jav"),
        connect_timeout_ms=int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "5000")),
    )
