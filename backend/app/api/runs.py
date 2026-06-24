from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query

from scraper.database.mongo_client import get_mongo_db
from backend.app.task_queue import run_to_response as to_response, get_queue_status, stop_current_task
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
    query = {}
    if status:
        query["status"] = status

    total = _col().count_documents(query)
    total_pages = max(1, (total + limit - 1) // limit)

    cursor = (
        _col()
        .find(query)
        .sort("queued_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )

    items = [to_response(d) for d in cursor]

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: str):
    try:
        oid = ObjectId(run_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid run ID")
    doc = _col().find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Run not found")
    return to_response(doc)


@router.post("/{run_id}/stop")
def stop_run(run_id: str):
    try:
        ObjectId(run_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid run ID")

    status = get_queue_status()
    if str(status.get("current_run_id")) != run_id:
        raise HTTPException(status_code=400, detail="Task is not currently running")

    stopped = stop_current_task()
    if not stopped:
        raise HTTPException(status_code=400, detail="No task is currently running")

    return {"success": True, "message": "Stop signal sent"}
