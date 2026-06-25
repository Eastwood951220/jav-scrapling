from dataclasses import dataclass
from typing import Any


@dataclass
class CrawlTask:
    name: str
    url: str
    url_type: str
    is_skip: bool = False
    has_magnet: bool = False
    has_chinese_sub: bool = False
    sort_type: int = 0
    max_list_pages: int = 50
    source: str | None = None
    final_url: str | None = None

    def get(self, key: str, default: Any = None) -> Any:
        try:
            if "." in key:
                current: Any = self
                for part in key.split("."):
                    current = getattr(current, part)
                return current
            return getattr(self, key, default)
        except AttributeError:
            return default

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "url_type": self.url_type,
            "is_skip": self.is_skip,
            "has_magnet": self.has_magnet,
            "has_chinese_sub": self.has_chinese_sub,
            "sort_type": self.sort_type,
            "max_list_pages": self.max_list_pages,
            "source": self.source,
            "final_url": self.final_url,
        }
