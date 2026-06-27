"""Tests for the refactored storage worker pipeline modules.

Covers domain helpers (path_policy, filename_policy, video_selector) and
worker components (scheduler, context, state machine).
"""

from unittest.mock import MagicMock


def test_path_policy_preserves_existing_target_rules():
    from app.modules.storage.domain.path_policy import all_target_folders, download_folder, target_folder

    task = {"task_id": "ST0001", "movie_code": "ABC-001", "source_task_name": ["taskA", "taskB"]}
    config = {"download_root_folder": "/Downloads", "target_folder": "/Movies", "use_task_subfolder": True}

    assert download_folder(task, config) == "/Downloads/ST0001"
    assert target_folder(task, config) == "/Movies/taskB/ABC-001"
    assert all_target_folders(task, config) == ["/Movies/taskA/ABC-001", "/Movies/taskB/ABC-001"]


def test_path_policy_download_folder_no_subfolder():
    from app.modules.storage.domain.path_policy import download_folder

    task = {"task_id": "ST0002", "movie_code": "XYZ-999"}
    config = {"download_root_folder": "/DL", "use_task_subfolder": False}

    assert download_folder(task, config) == "/DL"


def test_path_policy_target_folder_single_name():
    from app.modules.storage.domain.path_policy import target_folder

    task = {"task_id": "ST0003", "movie_code": "DEF-005", "source_task_name": "myTask"}
    config = {"target_folder": "/Movies"}

    assert target_folder(task, config) == "/Movies/myTask/DEF-005"


def test_path_policy_target_folder_empty_name():
    from app.modules.storage.domain.path_policy import target_folder

    task = {"task_id": "ST0004", "movie_code": "GHI-010", "source_task_name": ""}
    config = {"target_folder": "/Movies"}

    assert target_folder(task, config) == "/Movies/GHI-010"


def test_target_folder_with_code_suffix():
    from app.modules.storage.domain.path_policy import target_folder

    task = {"task_id": "ST0001", "movie_code": "SSIS-945", "source_task_name": "taskA"}
    config = {"target_folder": "/Movies"}

    assert target_folder(task, config, code_suffix="-C") == "/Movies/taskA/SSIS-945-C"
    assert target_folder(task, config, code_suffix="-U") == "/Movies/taskA/SSIS-945-U"
    assert target_folder(task, config, code_suffix="-UC") == "/Movies/taskA/SSIS-945-UC"
    assert target_folder(task, config, code_suffix="") == "/Movies/taskA/SSIS-945"


def test_all_target_folders_with_code_suffix():
    from app.modules.storage.domain.path_policy import all_target_folders

    task = {"task_id": "ST0001", "movie_code": "SSIS-945", "source_task_name": ["taskA", "taskB"]}
    config = {"target_folder": "/Movies"}

    assert all_target_folders(task, config, code_suffix="-C") == [
        "/Movies/taskA/SSIS-945-C",
        "/Movies/taskB/SSIS-945-C",
    ]
    assert all_target_folders(task, config, code_suffix="") == [
        "/Movies/taskA/SSIS-945",
        "/Movies/taskB/SSIS-945",
    ]


def test_filename_policy_multi_file_appends_cd_when_template_has_no_disc():
    from app.modules.storage.domain.filename_policy import build_video_name

    name = build_video_name(movie_code="ABC-001", original_name="part1.mkv", index=0, total=2, template="{code}{ext}")

    assert name == "ABC-001-CD1.mkv"


def test_filename_policy_single_file_uses_template_directly():
    from app.modules.storage.domain.filename_policy import build_video_name

    name = build_video_name(movie_code="ABC-001", original_name="movie.mkv", index=0, total=1, template="{code}{ext}")

    assert name == "ABC-001.mkv"


def test_filename_policy_multi_file_with_disc_in_template():
    from app.modules.storage.domain.filename_policy import build_video_name

    name = build_video_name(
        movie_code="ABC-001", original_name="part2.mkv", index=1, total=2, template="{code}-DISC{disc}{ext}"
    )

    assert name == "ABC-001-DISC2.mkv"


def test_filename_policy_disc_number_extraction():
    from app.modules.storage.domain.filename_policy import disc_number

    assert disc_number("movie_cd1.mkv") == 1
    assert disc_number("movie-CD2.mkv") == 2
    assert disc_number("movie_disc03.mkv") == 3
    assert disc_number("movie-part4.mkv") == 4
    assert disc_number("movie.mkv") is None


def test_video_selector_filters_by_extension_size_and_keyword():
    from app.modules.storage.domain.video_selector import select_files

    result = select_files(
        [
            {"name": "movie.mkv", "path": "/d/movie.mkv", "size": 200 * 1024 * 1024, "is_dir": False},
            {"name": "sample.mp4", "path": "/d/sample.mp4", "size": 200 * 1024 * 1024, "is_dir": False},
            {"name": "small.mp4", "path": "/d/small.mp4", "size": 1, "is_dir": False},
            {"name": "cover.jpg", "path": "/d/cover.jpg", "size": 1, "is_dir": False},
        ],
        {
            "video_extensions": [".mkv", ".mp4"],
            "minimum_video_size_mb": 100,
            "excluded_filename_keywords": ["sample"],
        },
    )

    assert [item["name"] for item in result.selected_videos] == ["movie.mkv"]
    assert [item["name"] for item in result.cover_files] == ["cover.jpg"]
    assert len(result.excluded_files) == 2


def test_video_selector_subtitle_detection():
    from app.modules.storage.domain.video_selector import select_files

    result = select_files(
        [
            {"name": "subs.srt", "path": "/d/subs.srt", "size": 1024, "is_dir": False},
            {"name": "subs.ass", "path": "/d/subs.ass", "size": 1024, "is_dir": False},
        ],
        {"video_extensions": [".mkv", ".mp4"], "minimum_video_size_mb": 100},
    )

    assert len(result.subtitle_files) == 2
    assert len(result.selected_videos) == 0


def test_scheduler_priority_order_calls_repositories():
    from app.modules.storage.worker.scheduler import StorageTaskScheduler

    repo = MagicMock()
    repo.find_next_executable.return_value = None
    repo.find_waiting_retry.return_value = {"task_id": "retry"}
    scheduler = StorageTaskScheduler(repo)

    assert scheduler.fetch_next_task()["task_id"] == "retry"
    repo.find_next_executable.assert_called_once()
    repo.find_waiting_retry.assert_called_once()


def test_scheduler_returns_first_available():
    from app.modules.storage.worker.scheduler import StorageTaskScheduler

    repo = MagicMock()
    repo.find_next_executable.return_value = {"task_id": "recovery"}
    scheduler = StorageTaskScheduler(repo)

    result = scheduler.fetch_next_task()
    assert result["task_id"] == "recovery"
    repo.find_next_executable.assert_called_once()
    repo.find_waiting_retry.assert_not_called()


def test_scheduler_returns_none_when_empty():
    from app.modules.storage.worker.scheduler import StorageTaskScheduler

    repo = MagicMock()
    repo.find_next_executable.return_value = None
    repo.find_waiting_retry.return_value = None
    repo.find_waiting_download.return_value = None
    repo.find_pending.return_value = None
    scheduler = StorageTaskScheduler(repo)

    assert scheduler.fetch_next_task() is None
    repo.find_pending.assert_called_once()


def test_state_machine_pipeline_steps_order():
    from app.modules.storage.worker.state_machine import PIPELINE_STEPS

    assert PIPELINE_STEPS == [
        "prepare",
        "submit_magnet",
        "waiting_download",
        "scan_files",
        "select_videos",
        "rename_files",
        "move_files",
        "verify_result",
        "cleanup_files",
    ]


def test_state_machine_skips_completed_steps():
    from app.modules.storage.worker.state_machine import StorageStateMachine

    prepare_step = MagicMock()
    prepare_step.name = "prepare"
    prepare_step.is_completed.return_value = True

    next_step = MagicMock()
    next_step.name = "submit_magnet"
    next_step.is_completed.return_value = False
    next_step.execute.return_value = {"task_id": "T1", "movie_id": "M1", "moved_files": []}

    # Remaining steps are all completed
    remaining_steps = []
    for step_name in [
        "waiting_download",
        "scan_files",
        "select_videos",
        "rename_files",
        "move_files",
        "verify_result",
        "cleanup_files",
    ]:
        s = MagicMock()
        s.name = step_name
        s.is_completed.return_value = True
        remaining_steps.append(s)

    state_machine = StorageStateMachine([prepare_step, next_step] + remaining_steps)

    context = MagicMock()
    context.task = {"task_id": "T1", "movie_id": "M1", "step": "prepare", "moved_files": []}

    state_machine.execute(context)

    prepare_step.execute.assert_not_called()
    next_step.execute.assert_called_once()


def test_prepare_step_is_completed_when_paths_set():
    from app.modules.storage.worker.steps.prepare import PrepareStep

    step = PrepareStep()
    context = MagicMock()
    context.task = {"download_path": "/DL/T1", "target_path": "/Movies/ABC-001"}

    assert step.is_completed(context) is True


def test_prepare_step_not_completed_when_paths_missing():
    from app.modules.storage.worker.steps.prepare import PrepareStep

    step = PrepareStep()
    context = MagicMock()
    context.task = {"download_path": None, "target_path": None}

    assert step.is_completed(context) is False


def test_prepare_step_derives_code_suffix():
    from app.modules.storage.worker.steps.prepare import PrepareStep

    step = PrepareStep()
    context = MagicMock()
    context.task = {
        "task_id": "ST0001",
        "movie_id": "60f7c2d4e13823a3c8b45678",
        "movie_code": "SSIS-945",
        "magnet_url": "magnet:?xt=urn:btih:abc123",
    }
    context.config = {
        "download_root_folder": "/Downloads",
        "target_folder": "/Movies",
        "use_task_subfolder": True,
    }
    context.movie_repository = MagicMock()
    context.movie_repository.get_by_id.return_value = {
        "_id": "60f7c2d4e13823a3c8b45678",
        "code": "SSIS-945",
        "source_task_name": "taskA",
    }
    context.magnet_repository = MagicMock()
    context.magnet_repository.find_by_url.return_value = {
        "magnet_url": "magnet:?xt=urn:btih:abc123",
        "has_chinese_sub": True,
        "tags": ["中文字幕"],
    }
    context.task_repository = MagicMock()

    result = step.execute(context)

    # Should derive -C suffix
    update_call = context.task_repository.update.call_args[0][1]
    assert update_call["code_suffix"] == "-C"
    assert "SSIS-945-C" in update_call["target_path"]


def test_filename_policy_single_file_with_code_suffix():
    from app.modules.storage.domain.filename_policy import build_video_name

    name = build_video_name(
        movie_code="SSIS-945", original_name="movie.mkv", index=0, total=1, template="{code}{ext}", code_suffix="-C"
    )

    assert name == "SSIS-945-C.mkv"


def test_rename_step_uses_code_suffix():
    from app.modules.storage.worker.steps.rename_files import RenameFilesStep

    step = RenameFilesStep()
    context = MagicMock()
    context.task = {
        "task_id": "ST0001",
        "movie_code": "SSIS-945",
        "code_suffix": "-C",
        "selected_videos": [
            {"name": "SSIS-945-C.mp4", "path": "/Downloads/ST0001/SSIS-945-C.mp4"}
        ],
    }
    context.config = {
        "single_filename_template": "{code}{ext}",
        "multi_filename_template": "{code}{ext}",
    }
    context.provider = MagicMock()
    context.provider.rename_file.return_value = MagicMock(success=True)
    context.task_repository = MagicMock()

    result = step.execute(context)

    video = result["selected_videos"][0]
    assert video["renamed_name"] == "SSIS-945-C.mp4"
