from unittest.mock import MagicMock

from shared.integrations.storage_providers.clouddrive2.exceptions import CloudDriveNotFoundError


def test_move_files_step_skips_missing_source_file():
    """When source file doesn't exist, skip it and log warning instead of failing."""
    from backend.app.modules.storage.worker.steps.move_files import MoveFilesStep

    step = MoveFilesStep()
    context = MagicMock()
    context.task = {
        "task_id": "ST0001",
        "selected_videos": [
            {"name": "SSIS-945.mp4", "path": "/115open/嘿嘿/日本/巨乳/SSIS-945.mp4"}
        ],
        "target_path": "/Movies/SSIS-945",
        "target_paths": ["/Movies/SSIS-945"],
    }
    context.config = {"auto_create_target_folder": True}
    context.provider = MagicMock()
    # find_file returns None for source (file doesn't exist)
    context.provider.find_file.return_value = None
    # find_file_by_path raises NOT_FOUND for source
    context.provider.find_file_by_path.side_effect = CloudDriveNotFoundError("not found")

    result = step.execute(context)

    # Should skip the missing file, not fail
    assert len(result["moved_files"]) == 0
    context.logger.log.assert_any_call(
        "跳过不存在的源文件: SSIS-945.mp4", "WARNING"
    )
    # Should NOT call move_files for missing source
    context.provider.move_files.assert_not_called()


def test_move_files_step_moves_existing_file():
    """When source file exists, move it normally."""
    from backend.app.modules.storage.worker.steps.move_files import MoveFilesStep

    step = MoveFilesStep()
    context = MagicMock()
    context.task = {
        "task_id": "ST0001",
        "selected_videos": [
            {"name": "SSIS-945.mp4", "path": "/115open/嘿嘿/日本/巨乳/SSIS-945.mp4"}
        ],
        "target_path": "/Movies/SSIS-945",
        "target_paths": ["/Movies/SSIS-945"],
    }
    context.config = {"auto_create_target_folder": True}
    context.provider = MagicMock()
    # find_file returns a file for target (idempotent check)
    mock_file = MagicMock()
    mock_file.size = 0  # Empty target, should proceed with move
    context.provider.find_file.return_value = mock_file
    context.provider.move_files.return_value = MagicMock(success=True, error_message=None)

    result = step.execute(context)

    # Should move the file
    assert len(result["moved_files"]) == 1
    context.provider.move_files.assert_called_once()


def test_rename_files_step_skips_missing_source_file():
    """When source file doesn't exist, skip it and log warning instead of failing."""
    from backend.app.modules.storage.worker.steps.rename_files import RenameFilesStep

    step = RenameFilesStep()
    context = MagicMock()
    context.task = {
        "task_id": "ST0001",
        "movie_code": "SSIS-945",
        "selected_videos": [
            {"name": "SSIS-945.mp4", "path": "/115open/嘿嘿/日本/巨乳/SSIS-945.mp4"}
        ],
    }
    context.config = {
        "single_filename_template": "{code}{ext}",
        "multi_filename_template": "{code}{ext}",
    }
    context.provider = MagicMock()
    # find_file returns None (file doesn't exist)
    context.provider.find_file.return_value = None
    # rename_file raises NOT_FOUND
    context.provider.rename_file.side_effect = CloudDriveNotFoundError("not found")

    result = step.execute(context)

    # Should skip the missing file, not fail
    assert len(result["selected_videos"]) == 1
    video = result["selected_videos"][0]
    assert "rename_error" in video
    assert "renamed_path" not in video
    context.logger.log.assert_any_call(
        "重命名失败: SSIS-945.mp4: not found", "ERROR"
    )


def test_move_files_step_skips_files_with_rename_error():
    """When a file has rename_error, skip it in move step."""
    from backend.app.modules.storage.worker.steps.move_files import MoveFilesStep

    step = MoveFilesStep()
    context = MagicMock()
    context.task = {
        "task_id": "ST0001",
        "selected_videos": [
            {
                "name": "SSIS-945.mp4",
                "path": "/115open/嘿嘿/日本/巨乳/SSIS-945.mp4",
                "rename_error": "not found",
            }
        ],
        "target_path": "/Movies/SSIS-945",
        "target_paths": ["/Movies/SSIS-945"],
    }
    context.config = {"auto_create_target_folder": True}
    context.provider = MagicMock()

    result = step.execute(context)

    # Should skip the file with rename_error
    assert len(result["moved_files"]) == 0
    assert len(result["skipped_files"]) == 1
    assert result["skipped_files"][0]["skip_reason"] == "rename_failed"
    context.provider.move_files.assert_not_called()
