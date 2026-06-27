from shared.database.indexes.content import ensure_content_indexes
from shared.database.indexes.crawler import ensure_crawler_indexes
from shared.database.indexes.storage import ensure_storage_indexes


def ensure_all_indexes(db) -> None:
    ensure_content_indexes(db)
    ensure_crawler_indexes(db)
    ensure_storage_indexes(db)
