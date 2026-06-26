import re
from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query

from app.db.collections import (
    MOVIES,
    MOVIE_MAGNETS,
    MOVIE_ACTORS,
    MOVIE_TAGS,
    CRAWL_COOKIES_CONFIG,
    CRAWL_RUNS,
    CRAWL_RUN_DETAIL_TASKS,
    CRAWL_SCHEDULES,
    CRAWL_CONFIG,
    CRAWL_TASKS,
    STORAGE_CONFIG,
    STORAGE_COUNTERS,
    STORAGE_TASKS,
)
from app.modules.content.movies.schemas import MovieListResponse
from scraper.database.mongo_client import get_mongo_db, sanitize_collection_name

router = APIRouter(prefix="/api/movies", tags=["movies"])

# Unified collection name for all movies
MOVIE_COLLECTION = MOVIES
MAGNET_COLLECTION = MOVIE_MAGNETS


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


def _public_magnet_doc(doc: dict) -> dict:
    name = doc.get("name") or doc.get("title") or ""
    size_text = doc.get("size_text") or ""
    return {
        "_id": str(doc["_id"]) if doc.get("_id") else "",
        "movie_id": doc.get("movie_id", ""),
        "magnet": doc.get("magnet", ""),
        "name": name,
        "title": name,
        "size": size_text,
        "size_mb": doc.get("size", 0.0),
        "size_text": size_text,
        "file_count": doc.get("file_count"),
        "file_text": doc.get("file_text", ""),
        "tags": doc.get("tags", []),
        "has_chinese_sub": bool(doc.get("has_chinese_sub")),
        "date": doc.get("date", ""),
        "dedupe_key": doc.get("dedupe_key", ""),
    }


def _attach_movie_magnets(movie_docs: list[dict], magnets_col) -> None:
    movie_ids = [str(doc["_id"]) for doc in movie_docs if doc.get("_id")]
    if not movie_ids:
        return

    grouped: dict[str, list[dict]] = {movie_id: [] for movie_id in movie_ids}
    cursor = magnets_col.find({"movie_id": {"$in": movie_ids}})
    for magnet in cursor:
        movie_id = magnet.get("movie_id")
        if movie_id in grouped:
            grouped[movie_id].append(_public_magnet_doc(magnet))

    for doc in movie_docs:
        doc["magnets"] = grouped.get(str(doc.get("_id")), [])


def _magnet_export_item(movie: dict, magnet: dict) -> dict:
    return {
        "code": movie.get("code") or movie.get("name", ""),
        "title": movie.get("title") or movie.get("name", ""),
        "magnet": magnet.get("magnet", ""),
        "name": magnet.get("name") or magnet.get("title") or "",
        "size": magnet.get("size_text") or "",
        "size_mb": magnet.get("size", 0.0),
    }


@router.get("/collections")
def list_collections():
    """List movie collections (backward-compatible, returns unified collection)."""
    return [MOVIE_COLLECTION]


@router.delete("/collections/{collection_name}")
def delete_collection(collection_name: str):
    """Delete a collection (backward-compatible). Blocks deletion of system and unified collections."""
    db = get_mongo_db()
    safe_name = sanitize_collection_name(collection_name)
    excluded = {
        MOVIE_COLLECTION,
        CRAWL_COOKIES_CONFIG,
        CRAWL_RUNS,
        CRAWL_RUN_DETAIL_TASKS,
        CRAWL_SCHEDULES,
        CRAWL_CONFIG,
        CRAWL_TASKS,
        STORAGE_CONFIG,
        STORAGE_COUNTERS,
        STORAGE_TASKS,
    }
    if safe_name in excluded:
        raise HTTPException(status_code=400, detail="不能删除系统集合或统一电影集合")
    names = db.list_collection_names()
    if safe_name not in names:
        raise HTTPException(status_code=404, detail="集合不存在")
    db.drop_collection(safe_name)
    return {"deleted": True, "collection": safe_name}


@router.get("/actors")
def list_actors():
    """Return deduplicated actor names."""
    db = get_mongo_db()
    col = db[MOVIE_ACTORS]
    return [doc["name"] for doc in col.find({}, {"name": 1, "_id": 0}).sort("name", 1)]


@router.get("/tags")
def list_tags():
    """Return deduplicated tag names."""
    db = get_mongo_db()
    col = db[MOVIE_TAGS]
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

    movie_docs = list(cursor)
    _attach_movie_magnets(movie_docs, db[MAGNET_COLLECTION])

    items = []
    for doc in movie_docs:
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

    movie_docs = list(col.find(query, {"code": 1, "title": 1, "name": 1}))
    movies_by_id = {str(doc["_id"]): doc for doc in movie_docs}
    movie_ids = list(movies_by_id)

    magnets = []
    if movie_ids:
        cursor = db[MAGNET_COLLECTION].find({"movie_id": {"$in": movie_ids}})
        for magnet in cursor:
            if not magnet.get("magnet"):
                continue
            movie = movies_by_id.get(magnet.get("movie_id"))
            if movie:
                magnets.append(_magnet_export_item(movie, magnet))

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

    _attach_movie_magnets([doc], db[MAGNET_COLLECTION])

    doc["_id"] = str(doc["_id"])
    return _stringify_objectids(doc)


@router.post("/{movie_id}/select-magnet")
def select_magnet(movie_id: str, body: dict):
    """Set the selected (best) magnet for a movie."""
    try:
        oid = ObjectId(movie_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid movie ID")

    dedupe_key = body.get("dedupe_key", "").strip()
    if not dedupe_key:
        raise HTTPException(status_code=400, detail="dedupe_key is required")

    db = get_mongo_db()
    col = db[MOVIE_COLLECTION]

    # Verify movie exists
    movie = col.find_one({"_id": oid}, {"_id": 1})
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    # Verify magnet exists for this movie
    magnet = db[MAGNET_COLLECTION].find_one({
        "movie_id": str(oid),
        "dedupe_key": dedupe_key,
    })
    if not magnet:
        raise HTTPException(status_code=404, detail="Magnet not found for this movie")

    # Update the movie's selected magnet
    col.update_one(
        {"_id": oid},
        {"$set": {"selected_magnet_dedupe_key": dedupe_key}},
    )

    return {"success": True, "selected_magnet_dedupe_key": dedupe_key}


@router.delete("/batch")
def delete_movies_batch(body: dict):
    """Delete multiple movies by IDs, including their magnets."""
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

    # Cascade: delete associated magnets for all deleted movies
    if result.deleted_count > 0:
        db[MAGNET_COLLECTION].delete_many({"movie_id": {"$in": ids}})

    return {"deleted": result.deleted_count}


@router.delete("/{movie_id}")
def delete_movie(movie_id: str):
    """Delete a single movie by ID, including its magnets."""
    try:
        oid = ObjectId(movie_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid movie ID")

    db = get_mongo_db()
    col = db[MOVIE_COLLECTION]
    result = col.delete_one({"_id": oid})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Movie not found")

    # Cascade: delete associated magnets
    db[MAGNET_COLLECTION].delete_many({"movie_id": movie_id})

    return {"deleted": True}
