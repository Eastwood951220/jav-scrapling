from scraper.pipelines.movie_pipeline import MoviePipeline


class TestMoviePipeline:
    def setup_method(self):
        self.pipeline = MoviePipeline()

    def test_process_item_returns_cleaned_dict_on_valid_item(self):
        item = {"title": "  ABC-123  ", "code": "ABC-123", "source_url": "http://example.com"}
        result = self.pipeline.process_item(item)
        assert result is not None
        assert result["title"] == "ABC-123"

    def test_process_item_returns_none_on_invalid_item(self):
        item = {"title": "", "code": "", "source_url": ""}
        result = self.pipeline.process_item(item)
        assert result is None

    def test_process_items_returns_count_of_valid_items(self):
        items = [
            {"title": "A", "code": "A"},
            {"title": "", "code": "", "source_url": ""},
            {"title": "B", "code": "B"},
        ]
        cleaned = self.pipeline.process_items(items)
        assert len(cleaned) == 2

    def test_has_chinese_sub_adds_tag(self):
        item = {"title": "test", "code": "T-001", "has_chinese_sub": True, "tags": ["4K"]}
        result = self.pipeline.process_item(item)
        assert "中文字幕" in result["tags"]
