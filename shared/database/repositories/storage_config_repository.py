from __future__ import annotations

from datetime import datetime, timezone

from shared.database import get_database
from shared.database.collections import STORAGE_CONFIG

CONFIG_KEY = {"_key": "default"}


def mask_token(token: str) -> str:
    if not token:
        return ""
    if len(token) < 8:
        return "****"
    return f"{'*' * 12}{token[-4:]}"


def is_masked_token(token: str) -> bool:
    if not token:
        return False
    prefix = token[:-4] if len(token) > 4 else token
    return len(prefix) >= 4 and set(prefix) == {"*"}


class StorageConfigRepository:
    def __init__(self, db=None, collection=None) -> None:
        self.collection = collection if collection is not None else (db or get_database())[STORAGE_CONFIG]

    def get_default(self) -> dict:
        doc = self.collection.find_one(CONFIG_KEY) or {}
        doc.pop("_id", None)
        doc.pop("_key", None)
        return doc

    def save_default(self, config: dict) -> dict:
        update_data = dict(config)
        incoming_token = update_data.get("api_token", "")
        if not incoming_token or is_masked_token(incoming_token):
            existing = self.collection.find_one(CONFIG_KEY) or {}
            update_data["api_token"] = existing.get("api_token", "")
        update_data["updated_at"] = datetime.now(timezone.utc)
        self.collection.update_one(CONFIG_KEY, {"$set": update_data}, upsert=True)
        return update_data

    def get_raw_token(self) -> str:
        return (self.collection.find_one(CONFIG_KEY) or {}).get("api_token", "")
