from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException

from app.core.bson import stringify_objectids
from app.db.collections import CRAWL_RUNS, CRAWL_RUN_DETAIL_TASKS, CRAWL_TASKS
from app.modules.crawler.runs.logs import delete_run_logs
from app.modules.crawler.runs.queue import enqueue_task
from app.modules.crawler.runs.schemas import RunResponse
from app.modules.crawler.tasks.schemas import TaskCreate, TaskUpdate
from scraper.database.mongo_client import get_mongo_db
from scraper.tasks.task_utils import build_final_url, determine_source

router = APIRouter(prefix="/api/crawler/tasks", tags=["crawler-tasks"])

TASKS_COLLECTION = CRAWL_TASKS


def _collection():
    return get_mongo_db()[TASKS_COLLECTION]


def _task_to_response(doc: dict) -> dict:
    return stringify_objectids(doc)


@router.get("")
def list_tasks():
    docs = list(_collection().find().sort("created_at", -1))
    return [_task_to_response(d) for d in docs]


@router.post("", status_code=201)
def create_task(body: TaskCreate):
    source = determine_source(body.url)
    final_url = build_final_url(
        url=body.url,
        url_type=body.url_type,
        has_magnet=body.has_magnet,
        has_chinese_sub=body.has_chinese_sub,
        sort_type=body.sort_type,
        source=source,
    )

    doc = {
        "name": body.name,
        "url": body.url,
        "url_type": body.url_type,
        "is_skip": body.is_skip,
        "has_magnet": body.has_magnet,
        "has_chinese_sub": body.has_chinese_sub,
        "sort_type": body.sort_type,
        "max_list_pages": body.max_list_pages,
        "source": source,
        "final_url": final_url,
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

    if "url" in update_data or "url_type" in update_data:
        current = _collection().find_one({"_id": oid})
        if not current:
            raise HTTPException(status_code=404, detail="Task not found")
        url = update_data.get("url", current["url"])
        url_type = update_data.get("url_type", current["url_type"])
        has_magnet = update_data.get("has_magnet", current.get("has_magnet", False))
        has_chinese_sub = update_data.get("has_chinese_sub", current.get("has_chinese_sub", False))
        sort_type = update_data.get("sort_type", current.get("sort_type", 0))
        source = determine_source(url)
        update_data["source"] = source
        update_data["final_url"] = build_final_url(
            url=url,
            url_type=url_type,
            has_magnet=has_magnet,
            has_chinese_sub=has_chinese_sub,
            sort_type=sort_type,
            source=source,
        )

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
def delete_task(task_id: str):
    import logging
    logger = logging.getLogger("tasks")

    try:
        oid = ObjectId(task_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid task ID")

    # 先获取任务文档以找到集合名称
    task_doc = _collection().find_one({"_id": oid})
    if not task_doc:
        raise HTTPException(status_code=404, detail="Task not found")

    # 检查是否有正在运行或排队中的任务
    runs_col = get_mongo_db()[CRAWL_RUNS]
    active_run = runs_col.find_one({
        "task_id": str(oid),
        "status": {"$in": ["running", "queued"]},
    })
    if active_run:
        raise HTTPException(status_code=400, detail="不能删除有运行中或排队中任务的配置")

    # 删除任务文档
    _collection().delete_one({"_id": oid})

    # 删除关联的运行记录及文件存储
    run_ids = [str(r["_id"]) for r in runs_col.find({"task_id": str(oid)}, {"_id": 1})]
    if run_ids:
        # 删除关联的详情任务
        detail_col = get_mongo_db()[CRAWL_RUN_DETAIL_TASKS]
        for rid in run_ids:
            detail_col.delete_many({"run_id": rid})
        runs_col.delete_many({"task_id": str(oid)})
        for run_id in run_ids:
            try:
                delete_run_logs(run_id)
            except Exception as e:
                logger.warning("删除运行文件失败 %s: %s", run_id, e)
        logger.info("已删除 %d 条运行记录", len(run_ids))

    return {"deleted": True}


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
