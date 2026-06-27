import re
from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query

from shared.database import get_database, sanitize_collection_name
from shared.database.collections import (
    MOVIES,
    MOVIE_MAGNETS,
    MOVIE_FILTERS,
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
        "weight": doc.get("weight", 0),
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
        "code": movie.get("code") or "",
        "title": movie.get("source_name") or "",
        "magnet": magnet.get("magnet", ""),
        "name": magnet.get("name") or magnet.get("title") or "",
        "size": magnet.get("size_text") or "",
        "size_mb": magnet.get("size", 0.0),
    }


def _build_cd2_gateway(config: dict):
    """Build a CloudDrive2Gateway from storage config."""
    from shared.integrations.storage_providers.clouddrive2.factory import CloudDriveClientFactory
    from shared.integrations.storage_providers.clouddrive2.gateway import CloudDrive2Gateway

    factory = CloudDriveClientFactory()
    client = factory.create(config)
    return CloudDrive2Gateway(client)


def _load_storage_config() -> dict:
    """Load the default storage config from MongoDB."""
    from app.modules.storage.config.schemas import StorageConfig

    db = get_database()
    doc = db[STORAGE_CONFIG].find_one({"_key": "default"})
    if not doc:
        return StorageConfig().model_dump()
    doc.pop("_id", None)
    doc.pop("_key", None)
    doc.pop("updated_at", None)
    defaults = StorageConfig().model_dump()
    return {**defaults, **doc}


def _check_location_exists(gateway, path: str) -> bool:
    """Check if a file exists on CloudDrive2 at the given path."""
    found = gateway.find_file(path)
    return found is not None


@router.get("/collections")
def list_collections():
    """List movie collections (backward-compatible, returns unified collection)."""
    return [MOVIE_COLLECTION]


@router.delete("/collections/{collection_name}")
def delete_collection(collection_name: str):
    """Delete a collection (backward-compatible). Blocks deletion of system and unified collections."""
    db = get_database()
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


_VALID_FILTER_TYPES = {"actor", "tag", "director", "maker", "series"}


@router.get("/filters")
def list_filters(type: str = Query(..., description="Filter type: actor, tag, director, maker, series")):
    """Return deduplicated filter names for the given type."""
    if type not in _VALID_FILTER_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid filter type: {type}. Valid: {_VALID_FILTER_TYPES}")
    db = get_database()
    col = db[MOVIE_FILTERS]
    return [
        doc["name"]
        for doc in col.find({"type": type}, {"name": 1, "_id": 0}).sort("name", 1)
    ]


@router.get("/task-names")
def list_task_names():
    """Return distinct source_task_name values from the movies collection."""
    db = get_database()
    col = db[MOVIE_COLLECTION]
    names = col.distinct("source_task_name")
    # source_task_name is a list field; distinct returns flat values
    # Filter out empty strings and sort
    unique_names = sorted({n for n in names if n and isinstance(n, str)})
    return [{"name": n} for n in unique_names]


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
    director: str | None = Query(default=None),
    maker: str | None = Query(default=None),
    series: str | None = Query(default=None),
    date_from: str | None = Query(default=None, description="YYYY-MM-DD"),
    date_to: str | None = Query(default=None, description="YYYY-MM-DD"),
    storage_status: str | None = Query(default=None, description="Filter by storage status: completed, failed, pending, etc."),
):
    """Get a paginated movie list with optional filters."""
    db = get_database()
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
            {"source_name": {"$regex": escaped, "$options": "i"}},
            {"code": {"$regex": escaped, "$options": "i"}},
            {"source_task_name": {"$regex": escaped, "$options": "i"}},
        ]

    if source_task_name:
        query["source_task_name"] = source_task_name

    if storage_status:
        query["storage_summary.last_status"] = storage_status

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

    if director:
        director_list = [d.strip() for d in director.split(",") if d.strip()]
        if len(director_list) == 1:
            query["director"] = director_list[0]
        elif director_list:
            query["director"] = {"$in": director_list}

    if maker:
        maker_list = [m.strip() for m in maker.split(",") if m.strip()]
        if len(maker_list) == 1:
            query["maker"] = maker_list[0]
        elif maker_list:
            query["maker"] = {"$in": maker_list}

    if series:
        series_list = [s.strip() for s in series.split(",") if s.strip()]
        if len(series_list) == 1:
            query["series"] = series_list[0]
        elif series_list:
            query["series"] = {"$in": series_list}

    total = col.count_documents(query)
    total_pages = max(1, (total + limit - 1) // limit)

    allowed_sort = {"created_at", "updated_at", "code", "source_name", "release_date", "rating"}
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
    director: str | None = Query(default=None),
    maker: str | None = Query(default=None),
    series: str | None = Query(default=None),
    date_from: str | None = Query(default=None, description="YYYY-MM-DD"),
    date_to: str | None = Query(default=None, description="YYYY-MM-DD"),
):
    """Return all magnets matching the query filters (no pagination) for export."""
    db = get_database()
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
            {"source_name": {"$regex": escaped, "$options": "i"}},
            {"code": {"$regex": escaped, "$options": "i"}},
            {"source_task_name": {"$regex": escaped, "$options": "i"}},
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

    if director:
        director_list = [d.strip() for d in director.split(",") if d.strip()]
        if len(director_list) == 1:
            query["director"] = director_list[0]
        elif director_list:
            query["director"] = {"$in": director_list}

    if maker:
        maker_list = [m.strip() for m in maker.split(",") if m.strip()]
        if len(maker_list) == 1:
            query["maker"] = maker_list[0]
        elif maker_list:
            query["maker"] = {"$in": maker_list}

    if series:
        series_list = [s.strip() for s in series.split(",") if s.strip()]
        if len(series_list) == 1:
            query["series"] = series_list[0]
        elif series_list:
            query["series"] = {"$in": series_list}

    movie_docs = list(col.find(query, {"code": 1, "source_name": 1}))
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


@router.post("/sync-location/batch")
def sync_movie_locations_batch(body: dict):
    """Batch check storage locations for multiple movies."""
    ids = body.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="ids is required")

    db = get_database()
    col = db[MOVIE_COLLECTION]
    config = _load_storage_config()
    gateway = _build_cd2_gateway(config)

    try:
        results = []
        for mid in ids:
            try:
                oid = ObjectId(mid)
            except InvalidId:
                results.append({"movie_id": mid, "error": "Invalid ID"})
                continue

            movie = col.find_one({"_id": oid})
            if not movie:
                results.append({"movie_id": mid, "error": "Not found"})
                continue

            locations = movie.get("storage_summary", {}).get("locations", [])
            if not locations:
                results.append({"movie_id": mid, "synced": False, "locations": [], "message": "No storage locations"})
                continue

            loc_results = []
            all_exist = True
            for loc in locations:
                path = loc.get("path", "")
                exists = _check_location_exists(gateway, path) if path else False
                if not exists:
                    all_exist = False
                loc_results.append({**loc, "exists": exists})

            new_status = "completed" if all_exist else "missing"
            col.update_one(
                {"_id": oid},
                {"$set": {
                    "storage_summary.last_status": new_status,
                    "storage_summary.locations": loc_results,
                    "storage_summary.synced_at": datetime.now(),
                }},
            )
            results.append({"movie_id": mid, "synced": all_exist, "locations": loc_results})

        return {"results": results, "total": len(results)}
    finally:
        gateway.client.close()


@router.get("/{movie_id}")
def get_movie(movie_id: str):
    """Get a single movie by ID."""
    try:
        oid = ObjectId(movie_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid movie ID")

    db = get_database()
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

    db = get_database()
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


@router.post("/{movie_id}/sync-location")
def sync_movie_location(movie_id: str):
    """Check storage locations on CloudDrive2 and update movie status."""
    try:
        oid = ObjectId(movie_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid movie ID")

    db = get_database()
    col = db[MOVIE_COLLECTION]
    movie = col.find_one({"_id": oid})
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    locations = movie.get("storage_summary", {}).get("locations", [])
    if not locations:
        return {"locations": [], "synced": False, "message": "No storage locations"}

    config = _load_storage_config()
    gateway = _build_cd2_gateway(config)
    try:
        results = []
        all_exist = True
        for loc in locations:
            path = loc.get("path", "")
            exists = _check_location_exists(gateway, path) if path else False
            if not exists:
                all_exist = False
            results.append({**loc, "exists": exists})

        # Update movie's storage status based on sync result
        new_status = "completed" if all_exist else "missing"
        col.update_one(
            {"_id": oid},
            {"$set": {
                "storage_summary.last_status": new_status,
                "storage_summary.locations": results,
                "storage_summary.synced_at": datetime.now(),
            }},
        )

        return {"locations": results, "synced": all_exist}
    finally:
        gateway.client.close()


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

    db = get_database()
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

    db = get_database()
    col = db[MOVIE_COLLECTION]
    result = col.delete_one({"_id": oid})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Movie not found")

    # Cascade: delete associated magnets
    db[MAGNET_COLLECTION].delete_many({"movie_id": movie_id})

    return {"deleted": True}
