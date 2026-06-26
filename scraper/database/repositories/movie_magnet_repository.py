from __future__ import annotations

from datetime import datetime
import hashlib
from typing import Any
from urllib.parse import parse_qs, urlparse

from pymongo.errors import PyMongoError

from app.db.collections import MOVIE_MAGNETS
from scraper.config.logging import get_logger
from scraper.database.indexes import ensure_magnet_indexes
from scraper.database.mongo_client import get_mongo_db


def extract_info_hash(magnet_url: str | None) -> str:
    if not magnet_url:
        return ""

    query = parse_qs(urlparse(magnet_url).query)
    for xt in query.get("xt", []):
        prefix = "urn:btih:"
        if xt.lower().startswith(prefix):
            return xt[len(prefix):].lower()
    return ""


def build_magnet_dedupe_key(movie_id: str, magnet: dict[str, Any]) -> str:
    info_hash = str(magnet.get("info_hash") or "").strip().lower()
    if not info_hash:
        info_hash = extract_info_hash(magnet.get("magnet") or magnet.get("magnet_url"))
    if info_hash:
        return info_hash

    parts = [
        str(movie_id),
        str(magnet.get("name") or ""),
        str(magnet.get("size_text") or ""),
        str(magnet.get("file_count") or ""),
        str(magnet.get("file_text") or ""),
        str(magnet.get("date") or ""),
    ]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()


class MovieMagnetRepository:
    COLLECTION_NAME = MOVIE_MAGNETS

    def __init__(self, db=None):
        self.logger = get_logger("movie_magnet_repository")
        self.db = db if db is not None else get_mongo_db()
        self.available = True
        self._indexes_ensured = False

    def _ensure_indexes(self) -> None:
        if not self._indexes_ensured:
            ensure_magnet_indexes(self.db, self.COLLECTION_NAME)
            self._indexes_ensured = True

    def get_collection(self):
        return self.db[self.COLLECTION_NAME]

    def upsert_many(
        self,
        movie_id: Any,
        movie: dict[str, Any],
        magnets: list[dict[str, Any]],
    ) -> int:
        if not self.available:
            return 0

        saved_count = 0
        movie_id_str = str(movie_id)

        try:
            self._ensure_indexes()
            collection = self.get_collection()
            for magnet in magnets:
                document = self._normalize(movie_id_str, movie, magnet)
                if document is None:
                    continue

                collection.update_one(
                    {
                        "movie_id": document["movie_id"],
                        "dedupe_key": document["dedupe_key"],
                    },
                    {
                        "$set": document,
                        "$setOnInsert": {"created_at": datetime.now()},
                    },
                    upsert=True,
                )
                saved_count += 1
        except PyMongoError as exc:
            self.available = False
            self.logger.warning("Failed to upsert movie magnets: %s", exc)

        return saved_count

    def _normalize(
        self,
        movie_id: str,
        movie: dict[str, Any],
        magnet: dict[str, Any],
    ) -> dict[str, Any] | None:
        magnet_url = str(magnet.get("magnet") or magnet.get("magnet_url") or "").strip()
        name = str(magnet.get("name") or "").strip()
        size_text = str(magnet.get("size_text") or "").strip()
        file_text = str(magnet.get("file_text") or "").strip()
        if not (magnet_url or name or size_text or file_text):
            return None

        info_hash = str(magnet.get("info_hash") or "").strip().lower()
        if not info_hash:
            info_hash = extract_info_hash(magnet_url)

        tags = magnet.get("tags")
        if not isinstance(tags, list):
            tags = []

        document = {
            "movie_id": movie_id,
            "movie_code": movie.get("code") or movie.get("movie_code") or "",
            "movie_title": movie.get("title") or movie.get("movie_title") or "",
            "source_url": movie.get("source_url") or "",
            "source_task_name": movie.get("source_task_name") or "",
            "magnet": magnet_url,
            "dedupe_key": build_magnet_dedupe_key(
                movie_id,
                {
                    **magnet,
                    "magnet": magnet_url,
                    "info_hash": info_hash,
                    "name": name,
                    "size_text": size_text,
                    "file_text": file_text,
                },
            ),
            "name": name,
            "size": self._to_float(magnet.get("size")),
            "size_text": size_text,
            "file_count": magnet.get("file_count"),
            "file_text": file_text,
            "tags": tags,
            "has_chinese_sub": bool(magnet.get("has_chinese_sub")),
            "date": magnet.get("date") or "",
            "updated_at": datetime.now(),
        }
        if info_hash:
            document["info_hash"] = info_hash
        return document

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
