from unittest.mock import MagicMock

from pymongo import ASCENDING, IndexModel

from scraper.database.indexes import MOVIE_INDEXES, ensure_indexes


def test_movie_indexes_defined():
    """MOVIE_INDEXES is non-empty and includes a unique code index."""
    assert len(MOVIE_INDEXES) > 0

    code_index = None
    for idx in MOVIE_INDEXES:
        assert isinstance(idx, IndexModel)
        if idx.document.get("name") == "idx_movie_code_unique":
            code_index = idx

    assert code_index is not None, "MOVIE_INDEXES must contain idx_movie_code_unique"
    assert code_index.document.get("unique") is True
    assert code_index.document.get("sparse") is True
    keys = dict(code_index.document["key"])
    assert keys == {"code": ASCENDING}


def test_ensure_indexes_calls_create():
    """ensure_indexes delegates to collection.create_indexes."""
    db = MagicMock()
    collection = MagicMock()
    db.__getitem__ = MagicMock(return_value=collection)

    ensure_indexes(db, collection_name="movies")

    db.__getitem__.assert_called_once_with("movies")
    collection.create_indexes.assert_called_once()


def test_ensure_indexes_uses_background():
    """All indexes are created with background=True."""
    db = MagicMock()
    collection = MagicMock()
    db.__getitem__ = MagicMock(return_value=collection)

    ensure_indexes(db, collection_name="movies")

    args, kwargs = collection.create_indexes.call_args
    index_list = args[0]
    assert kwargs.get("background") is True, "create_indexes must use background=True"

    # Verify the passed index list matches MOVIE_INDEXES
    assert len(index_list) == len(MOVIE_INDEXES)
    for idx in index_list:
        assert isinstance(idx, IndexModel)
