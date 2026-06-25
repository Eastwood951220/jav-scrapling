from pymongo import ASCENDING, DESCENDING, IndexModel


MOVIE_INDEXES: list[IndexModel] = [
    IndexModel(
        [("code", ASCENDING)],
        unique=True,
        sparse=True,
        name="idx_movie_code_unique",
    ),
    IndexModel(
        [("source_url", ASCENDING)],
        unique=True,
        sparse=True,
        name="idx_movie_source_url_unique",
    ),
    IndexModel(
        [("source_task_name", ASCENDING), ("code", ASCENDING)],
        name="idx_movie_source_task_code",
    ),
    IndexModel(
        [("release_date", DESCENDING)],
        name="idx_movie_release_date",
    ),
    IndexModel(
        [("rating", DESCENDING)],
        sparse=True,
        name="idx_movie_rating",
    ),
    IndexModel(
        [("created_at", DESCENDING)],
        name="idx_movie_created_at",
    ),
    IndexModel(
        [("updated_at", DESCENDING)],
        name="idx_movie_updated_at",
    ),
    IndexModel(
        [("title", ASCENDING), ("code", ASCENDING)],
        name="idx_movie_title_code",
    ),
]


def ensure_indexes(db, collection_name: str = "movies") -> None:
    """Ensure all movie indexes exist on the target collection."""
    collection = db[collection_name]
    collection.create_indexes(MOVIE_INDEXES)
