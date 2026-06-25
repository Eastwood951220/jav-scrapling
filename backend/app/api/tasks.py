from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException

from scraper.database.mongo_client import get_mongo_db
from app.models.run import RunResponse
from app.models.task import TaskCreate, TaskResponse, TaskUpdate
from scraper.tasks.task_utils import build_final_url, determine_source

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

TASKS_COLLECTION = "config_tasks"


def _collection():
    return get_mongo_db()[TASKS_COLLECTION]


def _sanitize_collection_name(name: str) -> str:
    return name.replace(" ", "_").replace(".", "_").replace("$", "_")


def _task_to_response(doc: dict) -> dict:
    return {**doc, "_id": str(doc["_id"])}


@router.get("")
def list_tasks():
    docs = list(_collection().find().sort("created_at", -1))
    return [_task_to_response(d) for d in docs]


@router.post("", status_code=201)
def create_task(body: TaskCreate):
    source = determine_source(body.url)
    filter_dict = body.filter.model_dump()
    final_url = build_final_url(
        url=body.url,
        url_type=body.url_type,
        filter_config=filter_dict,
        source=source,
    )

    doc = {
        "name": body.name,
        "url": body.url,
        "url_type": body.url_type,
        "is_skip": body.is_skip,
        "max_list_pages": body.max_list_pages,
        "filter": filter_dict,
        "source": source,
        "final_url": final_url,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    result = _collection().insert_one(doc)
    doc["_id"] = str(result.inserted_id)

    # 创建该任务对应的电影集合
    collection_name = _sanitize_collection_name(body.name)
    db = get_mongo_db()
    if collection_name not in db.list_collection_names():
        db.create_collection(collection_name)

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

    if "filter" in update_data and update_data["filter"] is not None:
        if hasattr(update_data["filter"], "model_dump"):
            update_data["filter"] = update_data["filter"].model_dump()

    if "url" in update_data or "url_type" in update_data:
        current = _collection().find_one({"_id": oid})
        if not current:
            raise HTTPException(status_code=404, detail="Task not found")
        url = update_data.get("url", current["url"])
        url_type = update_data.get("url_type", current["url_type"])
        source = determine_source(url)
        filter_dict = update_data.get("filter", current.get("filter", {}))
        update_data["source"] = source
        update_data["final_url"] = build_final_url(
            url=url, url_type=url_type, filter_config=filter_dict, source=source
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

    task_name = task_doc.get("name", "")

    # 删除任务文档
    _collection().delete_one({"_id": oid})

    # 删除关联的电影集合
    if task_name:
        collection_name = _sanitize_collection_name(task_name)
        db = get_mongo_db()
        if collection_name in db.list_collection_names():
            db.drop_collection(collection_name)
            logger.info("已删除集合 '%s' (任务: '%s')", collection_name, task_name)

    # 删除关联的运行记录及文件存储
    from app.run_storage import delete_run_dir
    runs_col = get_mongo_db()["task_runs"]
    run_ids = [str(r["_id"]) for r in runs_col.find({"task_id": str(oid)}, {"_id": 1})]
    if run_ids:
        runs_col.delete_many({"task_id": str(oid)})
        for run_id in run_ids:
            delete_run_dir(run_id)
        logger.info("已删除 %d 条运行记录 (任务: '%s')", len(run_ids), task_name)

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

    from app.task_queue import enqueue_task

    run_doc = enqueue_task(task_id)
    return run_doc
