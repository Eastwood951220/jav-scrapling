from shared.database.indexes.content import (
    MAGNET_INDEXES,
    MOVIE_FILTERS_INDEXES,
    MOVIE_INDEXES,
)


def ensure_indexes(db, collection_name: str = "movies") -> None:
    db[collection_name].create_indexes(MOVIE_INDEXES)


def ensure_magnet_indexes(db, collection_name: str = "movie_magnets") -> None:
    db[collection_name].create_indexes(MAGNET_INDEXES)


def ensure_filters_indexes(db, collection_name: str = "movie_filters") -> None:
    db[collection_name].create_indexes(MOVIE_FILTERS_INDEXES)
