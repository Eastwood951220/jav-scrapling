from shared.database.indexes.bootstrap import ensure_all_indexes
from shared.database.indexes.content import ensure_content_indexes
from shared.database.indexes.crawler import ensure_crawler_indexes
from shared.database.indexes.storage import ensure_storage_indexes

__all__ = [
    "ensure_all_indexes",
    "ensure_content_indexes",
    "ensure_crawler_indexes",
    "ensure_storage_indexes",
]
