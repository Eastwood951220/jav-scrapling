from shared.database.indexes.bootstrap import ensure_all_indexes


def ensure_backend_indexes(db) -> None:
    ensure_all_indexes(db)
