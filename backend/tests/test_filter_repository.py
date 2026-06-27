from unittest.mock import MagicMock

from scraper.database.repositories.filter_repository import sync_movie_filters


def test_sync_movie_filters_unified_collection():
    """sync_movie_filters writes all 5 filter types to movie_filters."""
    db = MagicMock()

    mock_movies = MagicMock()
    mock_movies.find.return_value = [
        {"actors": ["Alice", "Bob"], "tags": ["HD", "中文字幕"], "director": "DirA", "maker": "MakerX", "series": "Series1"},
        {"actors": ["Alice", "Charlie"], "tags": ["HD"], "director": "DirB", "maker": "MakerX", "series": ""},
        {"actors": [], "tags": [], "director": "", "maker": "", "series": "Series1"},
    ]
    mock_filters = MagicMock()
    mock_collections = {"movies": mock_movies, "movie_filters": mock_filters}
    db.__getitem__ = MagicMock(side_effect=lambda name: mock_collections[name])

    result = sync_movie_filters(db)

    assert result["actors"] == 3  # Alice, Bob, Charlie
    assert result["tags"] == 2    # HD, 中文字幕
    assert result["directors"] == 2  # DirA, DirB
    assert result["makers"] == 1     # MakerX
    assert result["series"] == 1     # Series1 (empty filtered out)

    mock_filters.drop.assert_called_once()
    mock_filters.insert_many.assert_called_once()
    inserted_docs = mock_filters.insert_many.call_args[0][0]
    types = {d["type"] for d in inserted_docs}
    assert types == {"actor", "tag", "director", "maker", "series"}


def test_sync_movie_filters_skips_empty_values():
    """Empty and whitespace-only values are excluded."""
    db = MagicMock()
    mock_movies = MagicMock()
    mock_movies.find.return_value = [
        {"actors": ["", "  ", "Alice"], "tags": [], "director": "", "maker": "  ", "series": ""},
    ]
    mock_filters = MagicMock()
    mock_collections = {"movies": mock_movies, "movie_filters": mock_filters}
    db.__getitem__ = MagicMock(side_effect=lambda name: mock_collections[name])

    result = sync_movie_filters(db)

    assert result["actors"] == 1
    assert result["directors"] == 0
    assert result["makers"] == 0
