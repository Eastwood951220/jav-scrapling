import logging
from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException

from app.core.bson import stringify_objectids
from shared.database import get_database
from shared.database.collections import CRAWL_RUNS, CRAWL_RUN_DETAIL_TASKS, CRAWL_TASKS, MOVIES, MOVIE_MAGNETS
from app.modules.crawler.runs.logs import delete_run_logs
from app.modules.crawler.runs.queue import enqueue_task
from app.modules.crawler.runs.schemas import RunResponse
from app.modules.crawler.tasks.schemas import TaskCreate, TaskUpdate, TaskUrlEntry, ExtractNameRequest
from shared.integrations.content_sources.javdb import (
    build_final_url,
    determine_source,
    is_security_check_page,
    parse_page_section_name,
)

router = APIRouter(prefix="/api/crawler/tasks", tags=["crawler-tasks"])

TASKS_COLLECTION = CRAWL_TASKS


@router.post("/extract-name")
def extract_name(body: ExtractNameRequest):
    """从目标页面提取名称，用于自动填充任务名称。"""
    logger = logging.getLogger("tasks")

    # search 类型从 URL 的 q 参数提取名称，无需爬虫
    if body.url_type == "search":
        try:
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(body.url)
            q_values = parse_qs(parsed.query).get("q", [])
            name = q_values[0].strip() if q_values else ""
            return {"name": name}
        except Exception:
            return {"name": ""}

    try:
        from scraper.config.sites import JAVDB_SITE
        from scraper.cookies.cookie_manager import CookieManager
        from scraper.config.settings import REQUEST_TIMEOUT
        from scraper.fetchers.scrapling_fetcher import ScraplingFetcher

        cookie_manager = CookieManager(JAVDB_SITE["cookie_file"])
        cookies = cookie_manager.load()

        fetcher = ScraplingFetcher(
            headers=JAVDB_SITE["headers"],
            cookies=cookies,
            timeout=REQUEST_TIMEOUT,
        )

        page = fetcher.get(body.url)

        if is_security_check_page(page):
            raise HTTPException(status_code=429, detail="触发安全验证，请稍后重试")

        name = parse_page_section_name(page, body.url_type)
        return {"name": name}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("提取名称失败 url=%s: %s", body.url, e)
        raise HTTPException(status_code=500, detail=f"提取名称失败: {e}")


def _collection():
    return get_database()[TASKS_COLLECTION]


def _task_to_response(doc: dict) -> dict:
    return stringify_objectids(doc)


def _check_name_unique(name: str, exclude_id: str | None = None) -> None:
    """Raise 409 if a task with this name already exists."""
    query: dict = {"name": name}
    if exclude_id:
        query["_id"] = {"$ne": ObjectId(exclude_id)}
    if _collection().find_one(query, {"_id": 1}):
        raise HTTPException(status_code=409, detail=f"任务名称 '{name}' 已存在")


def _check_urls_unique(urls: list[TaskUrlEntry]) -> None:
    """Raise 400 if any URL appears more than once in the list."""
    seen: set[str] = set()
    for entry in urls:
        if entry.url in seen:
            raise HTTPException(status_code=400, detail=f"URL 重复: {entry.url}")
        seen.add(entry.url)


@router.get("")
def list_tasks():
    docs = list(_collection().find().sort("created_at", -1))
    return [_task_to_response(d) for d in docs]


@router.post("", status_code=201)
def create_task(body: TaskCreate):
    _check_name_unique(body.name)
    _check_urls_unique(body.urls)
    url_entries = []
    for entry in body.urls:
        source = determine_source(entry.url)
        final_url = build_final_url(
            url=entry.url,
            url_type=entry.url_type,
            has_magnet=entry.has_magnet,
            has_chinese_sub=entry.has_chinese_sub,
            sort_type=entry.sort_type,
            source=source,
        )
        url_entries.append({
            "url": entry.url,
            "url_type": entry.url_type,
            "has_magnet": entry.has_magnet,
            "has_chinese_sub": entry.has_chinese_sub,
            "sort_type": entry.sort_type,
            "source": source,
            "final_url": final_url,
            "url_name": entry.url_name,
        })

    doc = {
        "name": body.name,
        "urls": url_entries,
        "is_skip": body.is_skip,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    result = _collection().insert_one(doc)
    doc["_id"] = str(result.inserted_id)

    return doc


@router.get("/{task_id}")
def get_task(task_id: str):
    try:
        oid = ObjectId(task_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid task ID")
    doc = _collection().find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(doc)


@router.put("/{task_id}")
def update_task(task_id: str, body: TaskUpdate):
    try:
        oid = ObjectId(task_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid task ID")

    update_data = body.model_dump(exclude_none=True)

    if "name" in update_data:
        _check_name_unique(update_data["name"], exclude_id=task_id)
    if body.urls is not None:
        _check_urls_unique(body.urls)

    if "urls" in update_data and update_data["urls"] is not None:
        url_entries = []
        for entry in update_data["urls"]:
            source = determine_source(entry["url"])
            final_url = build_final_url(
                url=entry["url"],
                url_type=entry["url_type"],
                has_magnet=entry.get("has_magnet", False),
                has_chinese_sub=entry.get("has_chinese_sub", False),
                sort_type=entry.get("sort_type", 0),
                source=source,
            )
            url_entries.append({
                "url": entry["url"],
                "url_type": entry["url_type"],
                "has_magnet": entry.get("has_magnet", False),
                "has_chinese_sub": entry.get("has_chinese_sub", False),
                "sort_type": entry.get("sort_type", 0),
                "source": source,
                "final_url": final_url,
                "url_name": entry.get("url_name"),
            })
        update_data["urls"] = url_entries

    update_data["updated_at"] = datetime.now()

    result = _collection().find_one_and_update(
        {"_id": oid},
        {"$set": update_data},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(result)


@router.delete("/{task_id}")
def delete_task(task_id: str, mode: str = "normal"):
    logger = logging.getLogger("tasks")

    if mode not in ("normal", "complete"):
        raise HTTPException(status_code=400, detail="mode must be 'normal' or 'complete'")

    try:
        oid = ObjectId(task_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid task ID")

    # Get task document to retrieve the task name
    task_doc = _collection().find_one({"_id": oid})
    if not task_doc:
        raise HTTPException(status_code=404, detail="Task not found")

    task_name = task_doc.get("name", "")

    # Check for active runs
    runs_col = get_database()[CRAWL_RUNS]
    active_run = runs_col.find_one({
        "task_id": str(oid),
        "status": {"$in": ["running", "queued"]},
    })
    if active_run:
        raise HTTPException(status_code=400, detail="不能删除有运行中或排队中任务的配置")

    # Delete the task document
    _collection().delete_one({"_id": oid})

    # Delete associated runs and detail tasks
    run_ids = [str(r["_id"]) for r in runs_col.find({"task_id": str(oid)}, {"_id": 1})]
    if run_ids:
        detail_col = get_database()[CRAWL_RUN_DETAIL_TASKS]
        for rid in run_ids:
            detail_col.delete_many({"run_id": rid})
        runs_col.delete_many({"task_id": str(oid)})
        for run_id in run_ids:
            try:
                delete_run_logs(run_id)
            except Exception as e:
                logger.warning("删除运行文件失败 %s: %s", run_id, e)
        logger.info("已删除 %d 条运行记录", len(run_ids))

    # Mode-specific cleanup
    movies_col = get_database()[MOVIES]
    movies_affected = 0
    magnets_deleted = 0

    if mode == "normal":
        # Remove task name from movies.source_task_name arrays
        if task_name:
            result = movies_col.update_many(
                {"source_task_name": task_name},
                {"$pull": {"source_task_name": task_name}},
            )
            movies_affected = result.modified_count
            logger.info("普通删除: 从 %d 部电影中移除 source_task_name='%s'", movies_affected, task_name)

    elif mode == "complete":
        # Delete movies where source_task_name contains this task name
        if task_name:
            # Find movie IDs first (for magnet cleanup)
            movie_ids = [
                str(m["_id"])
                for m in movies_col.find(
                    {"source_task_name": task_name},
                    {"_id": 1},
                )
            ]
            movies_affected = len(movie_ids)

            if movie_ids:
                # Delete associated magnets
                magnets_col = get_database()[MOVIE_MAGNETS]
                magnet_result = magnets_col.delete_many(
                    {"movie_id": {"$in": movie_ids}},
                )
                magnets_deleted = magnet_result.deleted_count

                # Delete movies
                movies_col.delete_many({"source_task_name": task_name})

                logger.info(
                    "彻底删除: 删除 %d 部电影和 %d 条磁力链接 (source_task_name='%s')",
                    movies_affected, magnets_deleted, task_name,
                )

    return {
        "deleted": True,
        "mode": mode,
        "movies_affected": movies_affected,
        "magnets_deleted": magnets_deleted,
    }


@router.post("/{task_id}/run", status_code=202, response_model=RunResponse)
def run_task(task_id: str):
    try:
        oid = ObjectId(task_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid task ID")
    doc = _collection().find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Task not found")

    run_doc = enqueue_task(task_id)
    return run_doc
