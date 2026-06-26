from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import configure_logging, get_app_logger
from app.db.indexes import ensure_backend_indexes
from app.modules.content.movies.router import router as movies_router
from app.modules.crawler.cookies.router import router as cookies_config_router
from app.modules.crawler.runs.router import router as runs_router
from app.modules.crawler.schedules.router import router as schedules_router
from app.modules.crawler.config.router import router as config_router
from app.modules.crawler.tasks.router import router as tasks_router
from app.modules.storage.config.router import router as storage_config_router
from app.modules.storage.tasks.router import router as storage_tasks_router
from app.modules.storage.tasks.worker import start_storage_worker, stop_storage_worker
from app.scheduler import start_scheduler
from scraper.config.settings import MONGO_DB_NAME
from scraper.database.mongo_client import connect_mongo, close_mongo, get_mongo_db

configure_logging()
_startup_logger = get_app_logger("startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _startup_logger.info("Starting Jav Scrapling backend...")
    try:
        _startup_logger.info("Connecting to MongoDB...")
        connect_mongo()
        _startup_logger.info("MongoDB connected successfully")
    except Exception:
        _startup_logger.exception("FATAL: Failed to connect to MongoDB")
        raise

    try:
        _startup_logger.info("Ensuring database indexes...")
        db = get_mongo_db()
        ensure_backend_indexes(db)
        _startup_logger.info("Database indexes ensured successfully")
    except Exception:
        _startup_logger.exception("FATAL: Failed to ensure database indexes")
        raise

    try:
        _startup_logger.info("Starting scheduler...")
        start_scheduler()
        _startup_logger.info("Scheduler started successfully")
    except Exception:
        _startup_logger.exception("FATAL: Failed to start scheduler")
        raise

    try:
        from app.modules.crawler.runs.queue import recover_orphaned_runs
        recovered = recover_orphaned_runs()
        if recovered > 0:
            _startup_logger.info("Recovered %d orphaned queued runs", recovered)
    except Exception:
        _startup_logger.exception("WARNING: Failed to recover orphaned runs")

    try:
        _startup_logger.info("Starting storage worker...")
        start_storage_worker()
        _startup_logger.info("Storage worker started successfully")
    except Exception:
        _startup_logger.exception("WARNING: Failed to start storage worker")

    _startup_logger.info("Backend startup complete, listening on port 18642")
    yield
    _startup_logger.info("Shutting down...")
    stop_storage_worker()
    close_mongo()
    _startup_logger.info("Backend stopped")


app = FastAPI(
    title="Jav Scrapling API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(movies_router)
app.include_router(schedules_router)
app.include_router(config_router)
app.include_router(runs_router)
app.include_router(tasks_router)
app.include_router(cookies_config_router)
app.include_router(storage_config_router)
app.include_router(storage_tasks_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "db": MONGO_DB_NAME}
