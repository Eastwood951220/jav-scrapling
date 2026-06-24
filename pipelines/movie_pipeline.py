from pipelines.base_pipeline import BasePipeline


class MoviePipeline(BasePipeline):
    def __init__(self, repository):
        self.repository = repository

    def process_items(self, items: list[dict]) -> int:
        saved_count = 0

        for item in items:
            if self.process_item(item):
                saved_count += 1

        return saved_count

    def process_item(self, item: dict) -> bool:
        clean_item = self.clean_item(item)

        if not self.is_valid_item(clean_item):
            return False

        result = self.repository.upsert_movie(clean_item)
        return result is not None

    def clean_item(self, item: dict) -> dict:
        title = item.get("title")

        if isinstance(title, str):
            item["title"] = title.strip()

        tags = item.get("tags")
        if isinstance(tags, list) and item.get("has_chinese_sub") and "中文字幕" not in tags:
            item["tags"] = [*tags, "中文字幕"]

        return item

    def is_valid_item(self, item: dict) -> bool:
        return bool(item.get("title") or item.get("code") or item.get("source_url"))
