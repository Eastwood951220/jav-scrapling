from __future__ import annotations

from shared.database import get_database
from shared.database.collections import MOVIE_MAGNETS


class MagnetRepository:
    def __init__(self, db=None, collection=None) -> None:
        self.collection = collection if collection is not None else (db or get_database())[MOVIE_MAGNETS]

    def list_by_movie_id(self, movie_id: str) -> list[dict]:
        return list(self.collection.find({"movie_id": movie_id}))


def select_best_magnet(magnets: list[dict]) -> dict | None:
    if not magnets:
        return None
    return sorted(
        magnets,
        key=lambda item: (
            bool(item.get("has_chinese_sub")),
            item.get("size") or 0,
            item.get("updated_at") or "",
        ),
        reverse=True,
    )[0]
