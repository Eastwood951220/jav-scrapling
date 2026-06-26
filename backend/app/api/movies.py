import re
from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query

from app.models.movie import MovieListResponse
from scraper.database.mongo_client import get_mongo_db, sanitize_collection_name

router = APIRouter(prefix="/api/movies", tags=["movies"])

# Unified collection name for all movies
MOVIE_COLLECTION = "movies"
ACTORS_COLLECTION = "movie_actors"
TAGS_COLLECTION = "movie_tags"


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


@router.post("/sync-filters")
def sync_filters():
    """Scan all movies, dedup actors/tags, and write to movie_actors/movie_tags."""
    db = get_mongo_db()
    col = db[MOVIE_COLLECTION]

    actors_set: set[str] = set()
    tags_set: set[str] = set()

    for doc in col.find({}, {"actors": 1, "tags": 1}):
        for actor in doc.get("actors", []):
            if isinstance(actor, str) and actor.strip():
                actors_set.add(actor.strip())
        for tag in doc.get("tags", []):
            if isinstance(tag, str) and tag.strip():
                tags_set.add(tag.strip())

    db[ACTORS_COLLECTION].drop()
    db[TAGS_COLLECTION].drop()

    if actors_set:
        db[ACTORS_COLLECTION].insert_many(
            [{"name": name} for name in sorted(actors_set)]
        )
    if tags_set:
        db[TAGS_COLLECTION].insert_many(
            [{"name": name} for name in sorted(tags_set)]
        )

    return {"actors": len(actors_set), "tags": len(tags_set)}


@router.get("/actors")
def list_actors():
    """Return deduplicated actor names."""
    db = get_mongo_db()
    col = db[ACTORS_COLLECTION]
    return [doc["name"] for doc in col.find({}, {"name": 1, "_id": 0}).sort("name", 1)]


@router.get("/tags")
def list_tags():
    """Return deduplicated tag names."""
    db = get_mongo_db()
    col = db[TAGS_COLLECTION]
    return [doc["name"] for doc in col.find({}, {"name": 1, "_id": 0}).sort("name", 1)]


@router.get("", response_model=MovieListResponse)
def list_movies(
    search: str | None = Query(default=None),
    source_task_name: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_order: int = Query(default=-1, ge=-1, le=1),
    rating_min: float | None = Query(default=None, ge=0, le=5),
    actors: str | None = Query(default=None),
    tags: str | None = Query(default=None),
    date_from: str | None = Query(default=None, description="YYYY-MM-DD"),
    date_to: str | None = Query(default=None, description="YYYY-MM-DD"),
):
    """Get a paginated movie list with optional filters."""
    db = get_mongo_db()
    col = db[MOVIE_COLLECTION]

    query = {}
    if date_from or date_to:
        created_at_filter = {}
        if date_from:
            created_at_filter["$gte"] = datetime.strptime(date_from, "%Y-%m-%d")
        if date_to:
            created_at_filter["$lte"] = datetime.strptime(date_to, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
        query["created_at"] = created_at_filter

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

    if actors:
        actor_list = [a.strip() for a in actors.split(",") if a.strip()]
        if actor_list:
            query["actors"] = {"$all": actor_list}

    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            query["tags"] = {"$all": tag_list}

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


@router.get("/magnets")
def export_magnets(
    search: str | None = Query(default=None),
    source_task_name: str | None = Query(default=None),
    rating_min: float | None = Query(default=None, ge=0, le=5),
    actors: str | None = Query(default=None),
    tags: str | None = Query(default=None),
    date_from: str | None = Query(default=None, description="YYYY-MM-DD"),
    date_to: str | None = Query(default=None, description="YYYY-MM-DD"),
):
    """Return all magnets matching the query filters (no pagination) for export."""
    db = get_mongo_db()
    col = db[MOVIE_COLLECTION]

    query = {}
    if date_from or date_to:
        created_at_filter = {}
        if date_from:
            created_at_filter["$gte"] = datetime.strptime(date_from, "%Y-%m-%d")
        if date_to:
            created_at_filter["$lte"] = datetime.strptime(date_to, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
        query["created_at"] = created_at_filter

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

    if actors:
        actor_list = [a.strip() for a in actors.split(",") if a.strip()]
        if actor_list:
            query["actors"] = {"$all": actor_list}

    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            query["tags"] = {"$all": tag_list}

    cursor = col.find(query, {"magnets": 1, "code": 1, "title": 1, "name": 1, "_id": 0})
    magnets = []
    for doc in cursor:
        for m in doc.get("magnets", []):
            if isinstance(m, dict) and m.get("magnet"):
                magnets.append({
                    "code": doc.get("code") or doc.get("name", ""),
                    "title": doc.get("title") or doc.get("name", ""),
                    "magnet": m["magnet"],
                    "size": m.get("size", ""),
                })

    return {"magnets": magnets, "total": len(magnets)}


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
