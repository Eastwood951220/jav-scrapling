from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query

from app.core.bson import stringify_objectids
from app.db.collections import RUNS, RUN_DETAIL_TASKS
from app.modules.crawler.runs.logs import delete_run_logs, load_run_logs
from app.modules.crawler.runs.queue import (
    get_queue_status,
    retry_detail_task,
    run_to_response as to_response,
    stop_current_task,
)
from app.modules.crawler.runs.detail_schemas import RunDetailTaskListResponse
from app.modules.crawler.runs.schemas import QueueStatusResponse, RunListResponse, RunResponse
from scraper.database.mongo_client import get_mongo_db

router = APIRouter(prefix="/api/crawler/runs", tags=["crawler-runs"])

COLLECTION = RUNS


def _col():
    return get_mongo_db()[COLLECTION]


@router.get("/queue-status", response_model=QueueStatusResponse)
def queue_status():
    return get_queue_status()


@router.get("", response_model=RunListResponse)
def list_runs(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    import logging

    logger = logging.getLogger("runs")

    query = {}
    if status:
        query["status"] = status

    total = _col().count_documents(query)
    total_pages = max(1, (total + limit - 1) // limit)

    # Exclude heavy fields from the list query projection
    cursor = (
        _col()
        .find(query)
        .sort("queued_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )

    items = []
    for doc in cursor:
        item = to_response(doc)
        if item is not None:
            # Ensure result does not contain items (defensive for old data)
            if item.get("result"):
                item["result"] = {key: value for key, value in item["result"].items() if key != "items"}
            # Set logs to empty list (not loaded in list view)
            item["logs"] = []
            items.append(item)
        else:
            logger.warning("Skipped unserializable run doc: %s", doc.get("_id"))

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: str):
    import logging

    logger = logging.getLogger("runs")

    try:
        oid = ObjectId(run_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid run ID")
    doc = _col().find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Run not found")

    result = to_response(doc)
    if result is None:
        logger.error("Failed to serialize run doc: %s", run_id)
        raise HTTPException(status_code=500, detail="Failed to serialize run data")

    result["logs"] = load_run_logs(run_id)

    return result


@router.post("/{run_id}/stop")
def stop_run(run_id: str):
    try:
        ObjectId(run_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid run ID")

    stopped = stop_current_task(run_id)
    if not stopped:
        raise HTTPException(status_code=400, detail="任务当前未在运行中")

    return {"success": True, "message": "停止信号已发送"}


@router.delete("/{run_id}")
def delete_run(run_id: str):
    import logging

    logger = logging.getLogger("runs")

    try:
        oid = ObjectId(run_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid run ID")

    # 不能删除正在运行的任务
    status = get_queue_status()
    current_id = status.get("current_run_id")
    if current_id and str(current_id) == run_id:
        raise HTTPException(status_code=400, detail="不能删除正在运行的任务")

    # 从 MongoDB 删除记录
    result = _col().delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Run not found")

    # 删除关联的详情任务
    detail_deleted = _detail_col().delete_many({"run_id": run_id})
    if detail_deleted.deleted_count > 0:
        logger.info("已删除 %d 条详情任务 %s", detail_deleted.deleted_count, run_id)

    # 删除文件存储
    try:
        if delete_run_logs(run_id):
            logger.info("已删除运行日志 %s", run_id)
    except Exception as e:
        logger.warning("删除运行文件失败 %s: %s", run_id, e)

    return {"deleted": True}


DETAIL_TASKS_COLLECTION = RUN_DETAIL_TASKS


def _detail_col():
    return get_mongo_db()[DETAIL_TASKS_COLLECTION]


@router.get("/{run_id}/tasks", response_model=RunDetailTaskListResponse)
def list_run_detail_tasks(
    run_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    try:
        ObjectId(run_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid run ID")

    total = _detail_col().count_documents({"run_id": run_id})
    total_pages = max(1, (total + limit - 1) // limit)

    cursor = (
        _detail_col()
        .find({"run_id": run_id})
        .sort("created_at", 1)
        .skip((page - 1) * limit)
        .limit(limit)
    )
    items = [stringify_objectids(doc) for doc in cursor]

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


@router.post("/{run_id}/tasks/{task_id}/retry-crawl")
def retry_crawl(run_id: str, task_id: str):
    try:
        ObjectId(run_id)
        ObjectId(task_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")

    doc = _detail_col().find_one({"_id": ObjectId(task_id), "run_id": run_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Detail task not found")
    if doc.get("status") != "crawl_failed":
        raise HTTPException(status_code=400, detail="只能重试爬取失败的任务")

    result = retry_detail_task(task_id, "crawl")
    return result


@router.post("/{run_id}/tasks/{task_id}/retry-save")
def retry_save(run_id: str, task_id: str):
    try:
        ObjectId(run_id)
        ObjectId(task_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")

    doc = _detail_col().find_one({"_id": ObjectId(task_id), "run_id": run_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Detail task not found")
    if doc.get("status") != "save_failed":
        raise HTTPException(status_code=400, detail="只能重试入库失败的任务")

    result = retry_detail_task(task_id, "save")
    return result
