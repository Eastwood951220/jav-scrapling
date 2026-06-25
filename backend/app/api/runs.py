from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query

from scraper.database.mongo_client import get_mongo_db
from app.task_queue import run_to_response as to_response, get_queue_status, stop_current_task
from app.models.run import QueueStatusResponse, RunListResponse, RunResponse

router = APIRouter(prefix="/api/runs", tags=["runs"])

COLLECTION = "task_runs"


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

    from app.run_storage import get_result_summary

    logger = logging.getLogger("runs")

    query = {}
    if status:
        query["status"] = status

    total = _col().count_documents(query)
    total_pages = max(1, (total + limit - 1) // limit)

    # Exclude heavy fields from the list query projection
    cursor = (
        _col()
        .find(query, {"logs": 0})
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
                item["result"] = get_result_summary(item["result"])
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

    from app.run_storage import load_logs, load_result

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

    # Load logs from file, fall back to MongoDB
    file_logs = load_logs(run_id)
    if file_logs:
        result["logs"] = file_logs
    # else: keep MongoDB logs (backward compat for old runs)

    # Load result from file, fall back to MongoDB
    file_result = load_result(run_id)
    if file_result is not None:
        result["result"] = file_result
    # else: keep MongoDB result (backward compat)

    return result


@router.post("/{run_id}/stop")
def stop_run(run_id: str):
    try:
        ObjectId(run_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid run ID")

    status = get_queue_status()
    current_id = status.get("current_run_id")
    if not current_id or str(current_id) != run_id:
        raise HTTPException(status_code=400, detail="任务当前未在运行中")

    stopped = stop_current_task()
    if not stopped:
        raise HTTPException(status_code=400, detail="无法停止任务")

    # 不在此处写入 MongoDB — 仅设置停止信号，由 worker 通过原子更新设置最终状态
    return {"success": True, "message": "停止信号已发送"}
