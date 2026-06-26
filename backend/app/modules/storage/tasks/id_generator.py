from datetime import datetime

from pymongo import ReturnDocument


def generate_storage_task_id(counters_collection, now: datetime | None = None) -> str:
    current = now or datetime.now()
    prefix = f"storage_{current.strftime('%Y%m%d')}_{current.strftime('%H%M%S')}"
    result = counters_collection.find_one_and_update(
        {"_key": prefix},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"{prefix}_{result['seq']}"
