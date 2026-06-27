from __future__ import annotations

from datetime import datetime
import hashlib
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from pymongo.errors import PyMongoError

from shared.database import get_database
from shared.database.collections import MOVIE_MAGNETS
from scraper.config.logging import get_logger
from scraper.database.indexes import ensure_magnet_indexes
from shared.database.repositories.magnet_repository import (
    MagnetRepository as _SharedMagnetRepository,
    select_best_magnet,
)


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


def _parse_size_mb(value) -> float:
    """Parse a size value (float, int, or string like '8.75GB') into MB."""
    if isinstance(value, (int, float)):
        return float(value)
    if not value:
        return 0.0
    size_str = str(value).strip().upper()
    match = re.match(r"([\d.]+)\s*(GB|MB|KB|TB)?", size_str)
    if not match:
        return 0.0
    number = float(match.group(1))
    unit = match.group(2) or "MB"
    multipliers = {"KB": 1 / 1024, "MB": 1, "GB": 1024, "TB": 1024 * 1024}
    return number * multipliers.get(unit, 1)


def _has_chinese_sub(magnet: dict) -> bool:
    """Check if a magnet has Chinese subtitles via field, tags, or title keywords."""
    if magnet.get("has_chinese_sub"):
        return True
    tags = magnet.get("tags") or []
    if any("字幕" in str(tag) or "中字" in str(tag) for tag in tags):
        return True
    title = (magnet.get("title") or magnet.get("name") or "").lower()
    return any(kw in title for kw in ["chs", "cht", "chinese", "中字", "中文", "字幕"])


def compute_magnet_weight(magnet: dict) -> int:
    """Compute a numeric weight score for a magnet.

    Higher score = better magnet. Factors:
    - Chinese subtitle + size > 2GB: +100000
    - Chinese subtitle (any size): +10000
    - Size in MB: +min(size_mb, 50000)
    - Fewer files: +max(0, 10000 - file_count * 100)

    Args:
        magnet: Magnet dict with size, has_chinese_sub, tags, file_count fields.

    Returns:
        Integer weight score (higher is better).
    """
    has_sub = _has_chinese_sub(magnet)
    size_mb = _parse_size_mb(magnet.get("size") or magnet.get("size_text"))
    is_large_sub = has_sub and size_mb > 2048

    file_count = magnet.get("file_count")
    if isinstance(file_count, (int, float)) and file_count > 0:
        file_penalty = max(0, 10000 - int(file_count) * 100)
    else:
        file_penalty = 5000  # unknown file count gets neutral score

    return int(is_large_sub * 100000 + has_sub * 10000 + min(size_mb, 50000) + file_penalty)


class MovieMagnetRepository(_SharedMagnetRepository):
    COLLECTION_NAME = MOVIE_MAGNETS

    def __init__(self, db=None):
        self.logger = get_logger("movie_magnet_repository")
        self.db = db if db is not None else get_database()
        self.available = True
        self._indexes_ensured = False
        # Initialize shared repository with the same collection
        super().__init__(collection=self.db[self.COLLECTION_NAME])

    def _ensure_indexes(self) -> None:
        if not self._indexes_ensured:
            ensure_magnet_indexes(self.db, self.COLLECTION_NAME)
            self._indexes_ensured = True

    def get_collection(self):
        return self.collection

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
                now = datetime.now()
                document = self._normalize(movie_id_str, movie, magnet, now)
                if document is None:
                    continue
                update = {
                    "$set": document,
                    "$setOnInsert": {"created_at": now},
                }
                if "info_hash" not in document:
                    update["$unset"] = {"info_hash": ""}

                collection.update_one(
                    {
                        "movie_id": document["movie_id"],
                        "dedupe_key": document["dedupe_key"],
                    },
                    update,
                    upsert=True,
                )
                saved_count += 1
        except PyMongoError as exc:
            self.available = False
            self.logger.warning("Failed to upsert movie magnets: %s", exc)

        return saved_count

    def auto_select_best_magnet(self, movie_id: str) -> str | None:
        """Select the best magnet for a movie and persist the selection.

        Queries all magnets for the given movie, ranks them using
        select_best_magnet(), and writes selected_magnet_dedupe_key
        to the movie document.

        Args:
            movie_id: The movie's ObjectId as a string.

        Returns:
            The selected dedupe_key, or None if no magnets found.
        """
        try:
            magnets = list(self.get_collection().find({"movie_id": movie_id}))
            best = select_best_magnet(magnets)
            if not best:
                return None

            dedupe_key = best.get("dedupe_key", "")
            if not dedupe_key:
                return None

            from bson import ObjectId
            from shared.database.collections import MOVIES

            self.db[MOVIES].update_one(
                {"_id": ObjectId(movie_id)},
                {"$set": {"selected_magnet_dedupe_key": dedupe_key}},
            )
            return dedupe_key
        except Exception as exc:
            self.logger.warning("Failed to auto-select best magnet for %s: %s", movie_id, exc)
            return None

    def _normalize(
        self,
        movie_id: str,
        movie: dict[str, Any],
        magnet: dict[str, Any],
        now: datetime,
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
            "movie_title": movie.get("source_name") or movie.get("movie_title") or "",
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
            "weight": compute_magnet_weight(magnet),
            "date": magnet.get("date") or "",
            "updated_at": now,
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
