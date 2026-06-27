from unittest.mock import MagicMock


def test_persist_crawled_item_auto_selects_best_magnet():
    """_persist_crawled_item calls auto_select_best_magnet after upserting magnets."""
    from app.modules.crawler.runs.queue import _persist_crawled_item

    repository = MagicMock()
    repository.upsert_movie.return_value = "movie_123"

    magnet_repository = MagicMock()
    magnet_repository.upsert_many.return_value = 3
    magnet_repository.auto_select_best_magnet.return_value = "dedupe_key_best"

    cleaned_item = {
        "code": "TEST-001",
        "source_name": "Test Movie",
        "magnets": [
            {"magnet": "magnet:?xt=urn:btih:aaa", "name": "a"},
            {"magnet": "magnet:?xt=urn:btih:bbb", "name": "b"},
        ],
    }

    result = _persist_crawled_item(repository, magnet_repository, cleaned_item)

    assert result == "movie_123"

    # Verify magnets were popped before upsert_movie
    movie_doc_arg = repository.upsert_movie.call_args[0][0]
    assert "magnets" not in movie_doc_arg

    # Verify upsert_many was called with the magnets
    magnet_repository.upsert_many.assert_called_once()
    assert magnet_repository.upsert_many.call_args[0][0] == "movie_123"

    # Verify auto_select was called
    magnet_repository.auto_select_best_magnet.assert_called_once_with("movie_123")


def test_persist_crawled_item_skips_auto_select_when_no_magnets():
    """auto_select_best_magnet is not called when there are no magnets."""
    from app.modules.crawler.runs.queue import _persist_crawled_item

    repository = MagicMock()
    repository.upsert_movie.return_value = "movie_456"
    magnet_repository = MagicMock()

    cleaned_item = {"code": "TEST-002", "magnets": []}

    result = _persist_crawled_item(repository, magnet_repository, cleaned_item)

    assert result == "movie_456"
    magnet_repository.upsert_many.assert_not_called()
    magnet_repository.auto_select_best_magnet.assert_not_called()


def test_persist_crawled_item_skips_auto_select_when_no_movie_id():
    """auto_select_best_magnet is not called when upsert_movie returns None."""
    from app.modules.crawler.runs.queue import _persist_crawled_item

    repository = MagicMock()
    repository.upsert_movie.return_value = None
    magnet_repository = MagicMock()

    cleaned_item = {"code": "TEST-003", "magnets": [{"magnet": "magnet:?xt=urn:btih:xxx"}]}

    result = _persist_crawled_item(repository, magnet_repository, cleaned_item)

    assert result is None
    magnet_repository.upsert_many.assert_not_called()
    magnet_repository.auto_select_best_magnet.assert_not_called()
