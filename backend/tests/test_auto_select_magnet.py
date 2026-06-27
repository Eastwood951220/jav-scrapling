from unittest.mock import MagicMock
from scraper.database.repositories.movie_magnet_repository import select_best_magnet, MovieMagnetRepository


def test_select_best_magnet_prefers_large_subtitle():
    """Best magnet = Chinese sub + size > 2GB over larger non-subtitle."""
    magnets = [
        {"magnet": "magnet:?xt=urn:btih:large", "name": "big", "size": 29573.12, "tags": ["高清"], "has_chinese_sub": False},
        {"magnet": "magnet:?xt=urn:btih:sub", "name": "sub", "size": 8960.0, "tags": ["字幕"], "has_chinese_sub": True},
    ]
    result = select_best_magnet(magnets)
    assert result["magnet"] == "magnet:?xt=urn:btih:sub"


def test_select_best_magnet_prefers_subtitle_over_size():
    """Chinese sub (any size) beats larger non-subtitle."""
    magnets = [
        {"magnet": "magnet:?xt=urn:btih:big", "name": "big", "size": 5000.0, "tags": [], "has_chinese_sub": False},
        {"magnet": "magnet:?xt=urn:btih:sub", "name": "sub", "size": 1000.0, "tags": ["字幕"], "has_chinese_sub": True},
    ]
    result = select_best_magnet(magnets)
    assert result["magnet"] == "magnet:?xt=urn:btih:sub"


def test_select_best_magnet_returns_none_for_empty():
    assert select_best_magnet([]) is None
    assert select_best_magnet(None) is None


def test_select_best_magnet_handles_string_size():
    """Supports legacy string size format like '8.75GB'."""
    magnets = [
        {"magnet_url": "magnet:?xt=urn:btih:small", "title": "small", "size": "900MB"},
        {"magnet_url": "magnet:?xt=urn:btih:big", "title": "big", "size": "2.5GB"},
    ]
    result = select_best_magnet(magnets)
    assert result["magnet_url"] == "magnet:?xt=urn:btih:big"


def test_auto_select_best_magnet_persists_dedupe_key():
    """auto_select_best_magnet writes selected_magnet_dedupe_key to movie doc."""
    from bson import ObjectId

    movie_oid = ObjectId()

    db = MagicMock()
    mock_magnets_col = MagicMock()
    mock_movies_col = MagicMock()

    mock_magnets_col.find.return_value = [
        {"movie_id": str(movie_oid), "dedupe_key": "key_a", "magnet": "magnet:?xt=urn:btih:a", "size": 1000.0, "has_chinese_sub": False, "tags": []},
        {"movie_id": str(movie_oid), "dedupe_key": "key_b", "magnet": "magnet:?xt=urn:btih:b", "size": 5000.0, "has_chinese_sub": True, "tags": ["字幕"]},
    ]

    def get_collection(name):
        if name == "movie_magnets":
            return mock_magnets_col
        if name == "movies":
            return mock_movies_col
        return MagicMock()

    db.__getitem__ = MagicMock(side_effect=get_collection)

    repo = MovieMagnetRepository(db=db)
    result = repo.auto_select_best_magnet(str(movie_oid))

    assert result == "key_b"
    mock_movies_col.update_one.assert_called_once()
    call_args = mock_movies_col.update_one.call_args
    assert call_args[0][0] == {"_id": movie_oid}
    assert call_args[0][1] == {"$set": {"selected_magnet_dedupe_key": "key_b"}}
