from pymongo import ASCENDING, DESCENDING, IndexModel

from shared.database.collections.content import MOVIES, MOVIE_FILTERS, MOVIE_MAGNETS

MOVIE_INDEXES: list[IndexModel] = [
    IndexModel([("code", ASCENDING)], unique=True, sparse=True, name="idx_movie_code_unique"),
    IndexModel([("source_url", ASCENDING)], unique=True, sparse=True, name="idx_movie_source_url_unique"),
    IndexModel([("source_task_name", ASCENDING)], name="idx_movie_source_task_name"),
    IndexModel([("release_date", DESCENDING)], name="idx_movie_release_date"),
    IndexModel([("rating", DESCENDING)], sparse=True, name="idx_movie_rating"),
    IndexModel([("created_at", DESCENDING)], name="idx_movie_created_at"),
    IndexModel([("updated_at", DESCENDING)], name="idx_movie_updated_at"),
    IndexModel([("source_name", ASCENDING)], name="idx_movie_source_name"),
]

MAGNET_INDEXES: list[IndexModel] = [
    IndexModel([("movie_id", ASCENDING), ("dedupe_key", ASCENDING)], unique=True, name="idx_movie_magnets_movie_dedupe"),
    IndexModel([("movie_id", ASCENDING)], name="idx_movie_magnets_movie_id"),
    IndexModel([("info_hash", ASCENDING)], sparse=True, name="idx_movie_magnets_info_hash"),
    IndexModel([("source_task_name", ASCENDING), ("movie_code", ASCENDING)], name="idx_movie_magnets_source_task"),
    IndexModel([("has_chinese_sub", DESCENDING), ("size", DESCENDING)], name="idx_movie_magnets_quality"),
    IndexModel([("updated_at", DESCENDING)], name="idx_movie_magnets_updated_at"),
]

MOVIE_FILTERS_INDEXES: list[IndexModel] = [
    IndexModel([("type", ASCENDING), ("name", ASCENDING)], unique=True, name="idx_movie_filters_type_name"),
    IndexModel([("type", ASCENDING)], name="idx_movie_filters_type"),
]


def ensure_content_indexes(db) -> None:
    db[MOVIES].create_indexes(MOVIE_INDEXES)
    db[MOVIE_MAGNETS].create_indexes(MAGNET_INDEXES)
    db[MOVIE_FILTERS].create_indexes(MOVIE_FILTERS_INDEXES)
