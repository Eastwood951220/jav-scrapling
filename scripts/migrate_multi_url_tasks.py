"""One-time migration: convert tasks to multi-URL format and source_task_name to list.

Usage:
    cd backend && PYTHONPATH=".:..:$PYTHONPATH" ../.venv/bin/python ../scripts/migrate_multi_url_tasks.py

Safe to re-run: only updates documents that haven't been migrated yet.
"""
from __future__ import annotations

from scraper.database.mongo_client import get_mongo_db
from app.db.collections import CRAWL_TASKS, MOVIES


def migrate_tasks(db) -> int:
    """Convert single-url tasks to urls array format."""
    col = db[CRAWL_TASKS]
    count = 0

    for doc in col.find({"urls": {"$exists": False}}):
        url_entry = {
            "url": doc.get("url", ""),
            "url_type": doc.get("url_type", ""),
            "has_magnet": doc.get("has_magnet", False),
            "has_chinese_sub": doc.get("has_chinese_sub", False),
            "sort_type": doc.get("sort_type", 0),
            "source": doc.get("source"),
            "final_url": doc.get("final_url"),
        }

        update = {
            "$set": {
                "urls": [url_entry],
                "updated_at": doc.get("updated_at"),
            },
            "$unset": {
                "url": "",
                "url_type": "",
                "has_magnet": "",
                "has_chinese_sub": "",
                "sort_type": "",
                "max_list_pages": "",
                "source": "",
                "final_url": "",
            },
        }

        col.update_one({"_id": doc["_id"]}, update)
        count += 1

    return count


def migrate_movies_source_task_name(db) -> int:
    """Convert source_task_name from string to list."""
    col = db[MOVIES]
    count = 0

    for doc in col.find({"source_task_name": {"$type": "string"}}):
        old_value = doc["source_task_name"]
        col.update_one(
            {"_id": doc["_id"]},
            {"$set": {"source_task_name": [old_value]}},
        )
        count += 1

    return count


def migrate_movies_remove_source_page(db) -> int:
    """Remove source_page field from movies."""
    col = db[MOVIES]
    result = col.update_many(
        {"source_page": {"$exists": True}},
        {"$unset": {"source_page": ""}},
    )
    return result.modified_count


def main():
    db = get_mongo_db()

    print("=== Migrating tasks to multi-URL format ===")
    task_count = migrate_tasks(db)
    print(f"  Migrated {task_count} tasks")

    print("=== Migrating source_task_name to list ===")
    movie_count = migrate_movies_source_task_name(db)
    print(f"  Migrated {movie_count} movies")

    print("=== Removing source_page from movies ===")
    page_count = migrate_movies_remove_source_page(db)
    print(f"  Updated {page_count} movies")

    print("Migration complete!")


if __name__ == "__main__":
    main()
