from unittest.mock import MagicMock


def test_create_storage_task_requires_movie():
    from app.modules.storage.tasks.service import StorageTaskService

    movie_repo = MagicMock()
    movie_repo.get_by_id.return_value = None
    service = StorageTaskService(task_repository=MagicMock(), movie_repository=movie_repo, magnet_repository=MagicMock())

    try:
        service.create_task({"movie_id": "60f7c2d4e13823a3c8b45678", "magnet_url": "magnet:?xt=urn:btih:abc"})
        assert False, "Expected LookupError"
    except LookupError as exc:
        assert "Movie not found" in str(exc)


def test_create_storage_task_creates_document_and_updates_movie_summary():
    from app.modules.storage.tasks.service import StorageTaskService

    task_repo = MagicMock()
    task_repo.get_by_movie_hash_status.return_value = None
    task_repo.create.side_effect = lambda doc: doc
    movie_repo = MagicMock()
    movie_repo.get_by_id.return_value = {"_id": "60f7c2d4e13823a3c8b45678", "code": "ABC-001", "source_name": "Movie"}

    service = StorageTaskService(task_repository=task_repo, movie_repository=movie_repo, magnet_repository=MagicMock())

    result = service.create_task({"movie_id": "60f7c2d4e13823a3c8b45678", "magnet_url": "magnet:?xt=urn:btih:ABC123"})

    assert result["status"] == "created"
    created_doc = task_repo.create.call_args[0][0]
    assert created_doc["movie_code"] == "ABC-001"
    assert created_doc["info_hash"] == "abc123"
    movie_repo.update_storage_summary.assert_called_once()


def test_create_storage_task_returns_existing_when_duplicate():
    from app.modules.storage.tasks.service import StorageTaskService

    existing_task = {"task_id": "storage_existing", "status": "pending"}
    task_repo = MagicMock()
    task_repo.get_by_movie_hash_status.return_value = existing_task
    movie_repo = MagicMock()
    movie_repo.get_by_id.return_value = {"_id": "60f7c2d4e13823a3c8b45678", "code": "ABC-001", "source_name": "Movie"}

    service = StorageTaskService(task_repository=task_repo, movie_repository=movie_repo, magnet_repository=MagicMock())

    result = service.create_task({"movie_id": "60f7c2d4e13823a3c8b45678", "magnet_url": "magnet:?xt=urn:btih:ABC123"})

    assert result["status"] == "existing"
    assert result["task_id"] == "storage_existing"
    task_repo.create.assert_not_called()


def test_create_storage_task_requires_movie_id():
    from app.modules.storage.tasks.service import StorageTaskService

    service = StorageTaskService(task_repository=MagicMock(), movie_repository=MagicMock(), magnet_repository=MagicMock())

    try:
        service.create_task({"magnet_url": "magnet:?xt=urn:btih:abc"})
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "movie_id" in str(exc)


def test_create_storage_task_requires_magnet_url():
    from app.modules.storage.tasks.service import StorageTaskService

    service = StorageTaskService(task_repository=MagicMock(), movie_repository=MagicMock(), magnet_repository=MagicMock())

    try:
        service.create_task({"movie_id": "60f7c2d4e13823a3c8b45678"})
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "magnet_url" in str(exc)


def test_batch_retry_updates_failed_tasks():
    from app.modules.storage.tasks.service import StorageTaskService

    mock_result = MagicMock()
    mock_result.modified_count = 2
    task_repo = MagicMock()
    task_repo.collection.update_many.return_value = mock_result

    service = StorageTaskService(task_repository=task_repo, movie_repository=MagicMock(), magnet_repository=MagicMock())

    result = service.batch_retry(["task1", "task2", "task3"])

    assert result["retried"] == 2
    assert result["skipped"] == 1


def test_create_storage_task_derives_code_suffix():
    from app.modules.storage.tasks.service import StorageTaskService

    task_repo = MagicMock()
    task_repo.get_by_movie_hash_status.return_value = None
    task_repo.create.side_effect = lambda doc: doc
    movie_repo = MagicMock()
    movie_repo.get_by_id.return_value = {"_id": "60f7c2d4e13823a3c8b45678", "code": "SSIS-945", "source_name": "Movie"}
    magnet_repo = MagicMock()
    magnet_repo.find_by_url.return_value = {
        "has_chinese_sub": True,
        "tags": ["中文字幕"],
    }

    service = StorageTaskService(task_repository=task_repo, movie_repository=movie_repo, magnet_repository=magnet_repo)

    result = service.create_task({"movie_id": "60f7c2d4e13823a3c8b45678", "magnet_url": "magnet:?xt=urn:btih:ABC123"})

    created_doc = task_repo.create.call_args[0][0]
    assert created_doc["code_suffix"] == "-C"


def test_batch_retry_requires_task_ids():
    from app.modules.storage.tasks.service import StorageTaskService

    service = StorageTaskService(task_repository=MagicMock(), movie_repository=MagicMock(), magnet_repository=MagicMock())

    try:
        service.batch_retry([])
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "task_ids" in str(exc)
