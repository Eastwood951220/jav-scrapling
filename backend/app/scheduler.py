from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()


def start_scheduler():
    from scraper.database.mongo_client import get_mongo_db

    col = get_mongo_db()["config_schedules"]
    for doc in col.find({"enabled": True}):
        _add_job(doc)

    scheduler.start()


def _add_job(schedule_doc: dict):
    job_id = str(schedule_doc["_id"])

    def run_scheduled_tasks():
        from scraper.services.movie_service import MovieService
        from scraper.database.mongo_client import get_mongo_db

        tasks_col = get_mongo_db()["config_tasks"]
        service = MovieService()

        for task_id in schedule_doc.get("task_ids", []):
            from bson import ObjectId
            doc = tasks_col.find_one({"_id": ObjectId(task_id)})
            if not doc:
                continue
            from scraper.tasks.task_utils import build_crawl_task_from_doc
            task = build_crawl_task_from_doc(doc)
            service.crawl_javdb_task(task)

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
