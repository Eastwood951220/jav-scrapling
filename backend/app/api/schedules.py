from datetime import datetime

from apscheduler.triggers.cron import CronTrigger
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException

from database.mongo_client import get_mongo_db
from app.models.schedule import ScheduleCreate, ScheduleUpdate
from app.scheduler import add_schedule_job, remove_schedule_job

router = APIRouter(prefix="/api/schedules", tags=["schedules"])

COLLECTION = "config_schedules"


def _col():
    return get_mongo_db()[COLLECTION]


def _validate_cron(expression: str) -> None:
    try:
        CronTrigger.from_crontab(expression)
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail=f"Invalid cron expression: {expression}")


def _to_response(doc: dict) -> dict:
    return {**doc, "_id": str(doc["_id"])}


@router.get("")
def list_schedules():
    docs = list(_col().find().sort("created_at", -1))
    return [_to_response(d) for d in docs]


@router.post("", status_code=201)
def create_schedule(body: ScheduleCreate):
    doc = {
        "name": body.name,
        "task_ids": body.task_ids,
        "cron_expression": body.cron_expression,
        "enabled": body.enabled,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    _validate_cron(body.cron_expression)
    result = _col().insert_one(doc)
    doc["_id"] = str(result.inserted_id)

    if body.enabled:
        doc["_id"] = result.inserted_id
        add_schedule_job(doc)
        doc["_id"] = str(result.inserted_id)

    return doc


@router.get("/{schedule_id}")
def get_schedule(schedule_id: str):
    try:
        oid = ObjectId(schedule_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid schedule ID")
    doc = _col().find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return _to_response(doc)


@router.put("/{schedule_id}")
def update_schedule(schedule_id: str, body: ScheduleUpdate):
    try:
        oid = ObjectId(schedule_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid schedule ID")

    update_data = body.model_dump(exclude_none=True)
    if body.cron_expression is not None:
        _validate_cron(body.cron_expression)
    update_data["updated_at"] = datetime.now()

    result = _col().find_one_and_update(
        {"_id": oid},
        {"$set": update_data},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Schedule not found")

    remove_schedule_job(schedule_id)
    if result.get("enabled", True):
        add_schedule_job(result)

    return _to_response(result)


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: str):
    try:
        oid = ObjectId(schedule_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid schedule ID")
    remove_schedule_job(schedule_id)
    result = _col().delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"deleted": True}
