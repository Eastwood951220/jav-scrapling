import re

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query

from app.models.movie import MovieListResponse
from scraper.database.mongo_client import get_mongo_db, sanitize_collection_name

router = APIRouter(prefix="/api/movies", tags=["movies"])

# Unified collection name for all movies
MOVIE_COLLECTION = "movies"


def _escape_regex(value: str) -> str:
    """Escape regex special characters."""
    return re.escape(value)


def _stringify_objectids(obj):
    """Recursively convert all ObjectId instances to strings."""
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _stringify_objectids(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_objectids(item) for item in obj]
    return obj


@router.get("/collections")
def list_collections():
    """List movie collections (backward-compatible, returns unified collection)."""
    return [MOVIE_COLLECTION]


@router.delete("/collections/{collection_name}")
def delete_collection(collection_name: str):
    """Delete a collection (backward-compatible). Blocks deletion of system and unified collections."""
    db = get_mongo_db()
    safe_name = sanitize_collection_name(collection_name)
    excluded = {"config_tasks", "config_schedules", "config_settings", "task_runs", MOVIE_COLLECTION}
    if safe_name in excluded:
        raise HTTPException(status_code=400, detail="不能删除系统集合或统一电影集合")
    names = db.list_collection_names()
    if safe_name not in names:
        raise HTTPException(status_code=404, detail="集合不存在")
    db.drop_collection(safe_name)
    return {"deleted": True, "collection": safe_name}


@router.get("", response_model=MovieListResponse)
def list_movies(
    search: str | None = Query(default=None),
    source_task_name: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_order: int = Query(default=-1, ge=-1, le=1),
    rating_min: float | None = Query(default=None, ge=0, le=5),
):
    """Get a paginated movie list with optional filters."""
    db = get_mongo_db()
    col = db[MOVIE_COLLECTION]

    query = {}
    if search:
        escaped = _escape_regex(search)
        query["$or"] = [
            {"title": {"$regex": escaped, "$options": "i"}},
            {"code": {"$regex": escaped, "$options": "i"}},
            {"name": {"$regex": escaped, "$options": "i"}},
        ]

    if source_task_name:
        query["source_task_name"] = source_task_name

    if rating_min is not None:
        query["rating"] = {"$gte": rating_min}

    total = col.count_documents(query)
    total_pages = max(1, (total + limit - 1) // limit)

    allowed_sort = {"created_at", "updated_at", "code", "title", "name", "release_date", "rating"}
    if sort_by not in allowed_sort:
        sort_by = "created_at"
    if sort_order not in (-1, 1):
        sort_order = -1

    cursor = col.find(query).sort(sort_by, sort_order).skip((page - 1) * limit).limit(limit)

    items = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(_stringify_objectids(doc))

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


@router.get("/{movie_id}")
def get_movie(movie_id: str):
    """Get a single movie by ID."""
    try:
        oid = ObjectId(movie_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid movie ID")

    db = get_mongo_db()
    col = db[MOVIE_COLLECTION]
    doc = col.find_one({"_id": oid})

    if not doc:
        raise HTTPException(status_code=404, detail="Movie not found")

    doc["_id"] = str(doc["_id"])
    return _stringify_objectids(doc)


@router.delete("/batch")
def delete_movies_batch(body: dict):
    """Delete multiple movies by IDs."""
    ids = body.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="ids 不能为空")

    oids = []
    for mid in ids:
        try:
            oids.append(ObjectId(mid))
        except InvalidId:
            raise HTTPException(status_code=400, detail=f"Invalid movie ID: {mid}")

    db = get_mongo_db()
    col = db[MOVIE_COLLECTION]
    result = col.delete_many({"_id": {"$in": oids}})

    return {"deleted": result.deleted_count}


@router.delete("/{movie_id}")
def delete_movie(movie_id: str):
    """Delete a single movie by ID."""
    try:
        oid = ObjectId(movie_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid movie ID")

    db = get_mongo_db()
    col = db[MOVIE_COLLECTION]
    result = col.delete_one({"_id": oid})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Movie not found")

    return {"deleted": True}
