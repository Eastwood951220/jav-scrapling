from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from shared.database.collections import CRAWL_SCHEDULES, CRAWL_TASKS

scheduler = BackgroundScheduler()


def start_scheduler():
    from shared.database import get_database

    col = get_database()[CRAWL_SCHEDULES]
    for doc in col.find({"enabled": True}):
        _add_job(doc)

    scheduler.start()


def _add_job(schedule_doc: dict):
    job_id = str(schedule_doc["_id"])

    def run_scheduled_tasks():
        from shared.database import get_database
        from app.modules.crawler.runs.queue import enqueue_task

        tasks_col = get_database()[CRAWL_TASKS]

        for task_id in schedule_doc.get("task_ids", []):
            from bson import ObjectId
            doc = tasks_col.find_one({"_id": ObjectId(task_id)})
            if not doc:
                continue
            enqueue_task(task_id)

    scheduler.add_job(
        run_scheduled_tasks,
        trigger=CronTrigger.from_crontab(schedule_doc["cron_expression"]),
        id=job_id,
        replace_existing=True,
    )


def add_schedule_job(schedule_doc: dict):
    _add_job(schedule_doc)


def remove_schedule_job(schedule_id: str):
    try:
        scheduler.remove_job(schedule_id)
    except Exception:
        pass
