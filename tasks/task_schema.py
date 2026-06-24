from dataclasses import dataclass, field
from typing import Any


@dataclass
class FilterConfig:
    only_chinese: bool = False
    exclude_multi_person: bool = False
    extra_filters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.extra_filters, dict):
            self.extra_filters = {}

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        return self.extra_filters.get(key, default)

    def has(self, key: str) -> bool:
        return hasattr(self, key) or key in self.extra_filters

    def to_dict(self) -> dict[str, Any]:
        data = {
            "only_chinese": self.only_chinese,
            "exclude_multi_person": self.exclude_multi_person,
        }
        data.update(self.extra_filters)
        return data


@dataclass
class CrawlTask:
    name: str
    url: str
    url_type: str
    is_skip: bool = False
    max_list_pages: int = 50
    filter: FilterConfig = field(default_factory=FilterConfig)
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
            "max_list_pages": self.max_list_pages,
            "filter": self.filter.to_dict(),
            "source": self.source,
            "final_url": self.final_url,
        }
