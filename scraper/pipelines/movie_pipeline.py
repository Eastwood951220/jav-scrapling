from scraper.pipelines.base_pipeline import BasePipeline


class MoviePipeline(BasePipeline):
    def process_items(self, items: list[dict]) -> list[dict]:
        cleaned: list[dict] = []

        for item in items:
            result = self.process_item(item)
            if result is not None:
                cleaned.append(result)

        return cleaned

    def process_item(self, item: dict) -> dict | None:
        clean_item = self.clean_item(item)

        if not self.is_valid_item(clean_item):
            return None

        return clean_item

    def clean_item(self, item: dict) -> dict:
        result = dict(item)

        title = item.get("title")
        if isinstance(title, str):
            result["title"] = title.strip()

        tags = item.get("tags")
        if isinstance(tags, list) and item.get("has_chinese_sub") and "中文字幕" not in tags:
            result["tags"] = [*tags, "中文字幕"]

        return result

    def is_valid_item(self, item: dict) -> bool:
        return bool(item.get("title") or item.get("code") or item.get("source_url"))
