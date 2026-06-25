"""One-time migration: move run logs from MongoDB to JSONL files.

Usage (pick one):

  1. Copy into running container, then exec:
     docker cp backend/scripts/migrate_runs_to_files.py scrapling-backend:/app/scripts/
     docker compose exec backend python scripts/migrate_runs_to_files.py

  2. Run from the host (MongoDB exposed on localhost:27018):
     MONGO_URI="mongodb://admin:admin123@localhost:27017/" python backend/scripts/migrate_runs_to_files.py
"""

import sys
from pathlib import Path

# Ensure project root and backend dir are on sys.path so both
# scraper.* and app.* imports resolve correctly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
for p in (str(PROJECT_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from scraper.database.mongo_client import get_mongo_db, connect_mongo
from app.run_storage import get_result_summary, save_logs


def migrate():
    connect_mongo()
    db = get_mongo_db()
    runs = db["task_runs"]

    total = runs.count_documents({})
    migrated = 0
    skipped = 0

    print(f"Found {total} run documents to process")

    for doc in runs.find():
        run_id = str(doc["_id"])
        logs = doc.get("logs", [])
        result = doc.get("result")

        if not logs and result is None:
            skipped += 1
            continue

        if logs:
            save_logs(run_id, logs)

        if result and "items" in result:
            summary = get_result_summary(result)
            runs.update_one(
                {"_id": doc["_id"]},
                {"$set": {"result": summary, "logs": []}},
            )
        elif logs:
            # Clear logs from MongoDB even if no result
            runs.update_one(
                {"_id": doc["_id"]},
                {"$set": {"logs": []}},
            )

        migrated += 1
        if migrated % 10 == 0:
            print(f"  migrated {migrated}/{total}")

    print(f"Done: {migrated} migrated, {skipped} skipped (already clean)")


if __name__ == "__main__":
    migrate()
