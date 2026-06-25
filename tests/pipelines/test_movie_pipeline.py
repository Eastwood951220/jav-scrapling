import pytest
from scraper.pipelines.movie_pipeline import MoviePipeline


@pytest.fixture
def pipeline():
    return MoviePipeline()


class TestProcessItemAddsSourceTaskName:
    def test_adds_source_task_name_when_provided(self, pipeline):
        item = {"title": "Test Movie", "code": "ABC-123"}
        result = pipeline.process_item(item, task_name="my_task")
        assert result["source_task_name"] == "my_task"

    def test_no_source_task_name_when_not_provided(self, pipeline):
        item = {"title": "Test Movie", "code": "ABC-123"}
        result = pipeline.process_item(item)
        assert "source_task_name" not in result

    def test_no_source_task_name_when_none(self, pipeline):
        item = {"title": "Test Movie", "code": "ABC-123"}
        result = pipeline.process_item(item, task_name=None)
        assert "source_task_name" not in result

    def test_no_source_task_name_when_empty_string(self, pipeline):
        item = {"title": "Test Movie", "code": "ABC-123"}
        result = pipeline.process_item(item, task_name="")
        assert "source_task_name" not in result


class TestProcessItemStripsTitleWhitespace:
    def test_strips_leading_and_trailing_whitespace(self, pipeline):
        item = {"title": "  Test Movie  ", "code": "ABC-123"}
        result = pipeline.process_item(item)
        assert result["title"] == "Test Movie"

    def test_handles_no_whitespace(self, pipeline):
        item = {"title": "Test Movie", "code": "ABC-123"}
        result = pipeline.process_item(item)
        assert result["title"] == "Test Movie"

    def test_handles_missing_title(self, pipeline):
        item = {"code": "ABC-123"}
        result = pipeline.process_item(item)
        assert "title" not in result

    def test_handles_non_string_title(self, pipeline):
        item = {"title": 123, "code": "ABC-123"}
        result = pipeline.process_item(item)
        assert result["title"] == 123


class TestProcessItemAppendsChineseSubTag:
    def test_appends_tag_when_has_chinese_sub(self, pipeline):
        item = {"title": "Test", "code": "ABC-123", "has_chinese_sub": True, "tags": ["tag1"]}
        result = pipeline.process_item(item)
        assert "中文字幕" in result["tags"]
        assert "tag1" in result["tags"]

    def test_does_not_duplicate_existing_tag(self, pipeline):
        item = {
            "title": "Test",
            "code": "ABC-123",
            "has_chinese_sub": True,
            "tags": ["中文字幕", "tag1"],
        }
        result = pipeline.process_item(item)
        assert result["tags"].count("中文字幕") == 1

    def test_no_tag_when_no_chinese_sub(self, pipeline):
        item = {"title": "Test", "code": "ABC-123", "has_chinese_sub": False, "tags": ["tag1"]}
        result = pipeline.process_item(item)
        assert "中文字幕" not in result["tags"]


class TestProcessItemHandlesMissingTags:
    def test_creates_tags_list_when_missing(self, pipeline):
        item = {"title": "Test", "code": "ABC-123", "has_chinese_sub": True}
        result = pipeline.process_item(item)
        assert result["tags"] == ["中文字幕"]

    def test_handles_none_tags(self, pipeline):
        item = {"title": "Test", "code": "ABC-123", "has_chinese_sub": True, "tags": None}
        result = pipeline.process_item(item)
        # None is not a list, so the tag logic should not run
        assert "tags" not in result or result["tags"] is None


class TestProcessItemDoesNotMutateOriginal:
    def test_original_item_unchanged(self, pipeline):
        item = {"title": "  Test  ", "code": "ABC-123", "has_chinese_sub": True, "tags": []}
        original_tags = item["tags"]
        pipeline.process_item(item, task_name="task1")
        assert item["title"] == "  Test  "
        assert item["tags"] is original_tags
        assert "source_task_name" not in item


class TestProcessItems:
    def test_process_items_passes_task_name(self, pipeline):
        items = [
            {"title": "Movie 1", "code": "A-001"},
            {"title": "Movie 2", "code": "A-002"},
        ]
        results = pipeline.process_items(items, task_name="batch_task")
        assert len(results) == 2
        assert all(r["source_task_name"] == "batch_task" for r in results)

    def test_process_items_without_task_name(self, pipeline):
        items = [
            {"title": "Movie 1", "code": "A-001"},
            {"title": "Movie 2", "code": "A-002"},
        ]
        results = pipeline.process_items(items)
        assert len(results) == 2
        assert all("source_task_name" not in r for r in results)

    def test_process_items_filters_invalid(self, pipeline):
        items = [
            {"title": "Valid", "code": "A-001"},
            {},  # invalid - no title, code, or source_url
        ]
        results = pipeline.process_items(items, task_name="task1")
        assert len(results) == 1
