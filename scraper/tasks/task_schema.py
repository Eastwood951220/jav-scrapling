from dataclasses import dataclass, field
from typing import Any


@dataclass
class CrawlTaskUrlEntry:
    """A single URL entry within a crawl task."""
    url: str
    url_type: str
    has_magnet: bool = False
    has_chinese_sub: bool = False
    sort_type: int = 0
    source: str | None = None
    final_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "url_type": self.url_type,
            "has_magnet": self.has_magnet,
            "has_chinese_sub": self.has_chinese_sub,
            "sort_type": self.sort_type,
            "source": self.source,
            "final_url": self.final_url,
        }


@dataclass
class CrawlTask:
    name: str
    urls: list[CrawlTaskUrlEntry] = field(default_factory=list)
    is_skip: bool = False
    filter: dict[str, Any] | None = None

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
            "urls": [u.to_dict() for u in self.urls],
            "is_skip": self.is_skip,
            "filter": self.filter,
        }
