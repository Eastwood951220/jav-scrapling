from tasks.task_loader import TaskLoader


def test_task_loader_loads_multiple_tasks(tmp_path):
    task_file = tmp_path / "task.yml"
    task_file.write_text(
        "tasks:\n"
        "  - name: VR\n"
        "    url: https://javdb.com/actors/ZXy46?t=d&sort_type=0\n"
        "    url_type: actors\n"
        "    is_skip: false\n"
        "    filter:\n"
        "      only_chinese: false\n"
        "      exclude_multi_person: false\n"
        "      rating_min: 4.5\n"
        "  - name: List\n"
        "    url: https://javdb.com/lists/y1Zrb\n"
        "    url_type: lists\n"
        "    is_skip: true\n"
        "    filter:\n"
        "      only_chinese: true\n",
        encoding="utf-8",
    )

    loader = TaskLoader(task_file)
    tasks = loader.load_tasks()

    assert len(tasks) == 2
    assert tasks[0].name == "VR"
    assert tasks[0].max_list_pages == 50
    assert tasks[0].filter.exclude_multi_person is False
    assert tasks[0].filter.get("rating_min") == 4.5
    assert tasks[0].get("filter.only_chinese") is False
    assert tasks[1].is_skip is True
    assert tasks[1].filter.only_chinese is True


def test_task_loader_limits_max_pages(tmp_path):
    task_file = tmp_path / "task.yml"
    task_file.write_text(
        "tasks:\n"
        "  - name: VR\n"
        "    url: https://javdb.com/actors/ZXy46\n"
        "    url_type: actors\n"
        "    max_list_pages: 100\n",
        encoding="utf-8",
    )

    loader = TaskLoader(task_file)
    tasks = loader.load_tasks()

    assert tasks[0].max_list_pages == 50


def test_task_loader_fallback_javdb_config(tmp_path):
    task_file = tmp_path / "task.yml"
    task_file.write_text(
        "javdb:\n"
        "  enabled: true\n"
        "  keyword: SSIS\n"
        "  max_list_pages: 3\n",
        encoding="utf-8",
    )

    loader = TaskLoader(task_file)
    tasks = loader.load_tasks()

    assert len(tasks) == 1
    assert tasks[0].name == "SSIS"
    assert tasks[0].url_type == "search"
    assert tasks[0].max_list_pages == 3
    assert "q=SSIS" in tasks[0].final_url
