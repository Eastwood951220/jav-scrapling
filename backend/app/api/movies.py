import re

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query

from scraper.database.mongo_client import get_mongo_db, sanitize_collection_name

router = APIRouter(prefix="/api/movies", tags=["movies"])


def _escape_regex(value: str) -> str:
    return re.escape(value)


@router.get("/collections")
def list_collections():
    db = get_mongo_db()
    names = db.list_collection_names()
    excluded = {"config_tasks", "config_schedules", "config_settings", "task_runs"}
    return [n for n in names if n not in excluded]


@router.delete("/collections/{collection_name}")
def delete_collection(collection_name: str):
    db = get_mongo_db()
    safe_name = sanitize_collection_name(collection_name)
    excluded = {"config_tasks", "config_schedules", "config_settings", "task_runs"}
    if safe_name in excluded:
        raise HTTPException(status_code=400, detail="不能删除系统集合")
    names = db.list_collection_names()
    if safe_name not in names:
        raise HTTPException(status_code=404, detail="集合不存在")
    db.drop_collection(safe_name)
    return {"deleted": True, "collection": safe_name}


@router.get("")
def list_movies(
    collection: str = Query(default="movies"),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="release_date"),
    sort_order: int = Query(default=-1, ge=-1, le=1),
    rating_min: float | None = Query(default=None, ge=0, le=5),
):
    col = get_mongo_db()[sanitize_collection_name(collection)]

    query = {}
    if search:
        query["$or"] = [
            {"title": {"$regex": _escape_regex(search), "$options": "i"}},
            {"code": {"$regex": _escape_regex(search), "$options": "i"}},
            {"name": {"$regex": _escape_regex(search), "$options": "i"}},
        ]

    if rating_min is not None:
        query["rating"] = {"$gte": rating_min}

    total = col.count_documents(query)
    total_pages = max(1, (total + limit - 1) // limit)

    allowed_sort = {"created_at", "updated_at", "code", "title", "name", "release_date", "rating"}
    if sort_by not in allowed_sort:
        sort_by = "release_date"
    if sort_order not in (-1, 1):
        sort_order = -1

    cursor = col.find(query).sort(sort_by, sort_order).skip((page - 1) * limit).limit(limit)

    items = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


@router.get("/{movie_id}")
def get_movie(movie_id: str, collection: str = Query(default="movies")):
    try:
        oid = ObjectId(movie_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid movie ID")
    col = get_mongo_db()[sanitize_collection_name(collection)]
    doc = col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Movie not found")
    doc["_id"] = str(doc["_id"])
    return doc
