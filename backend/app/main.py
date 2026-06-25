import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from scraper.config.settings import MONGO_DB_NAME
from scraper.database.mongo_client import connect_mongo, close_mongo, get_mongo_db
from scraper.database.indexes import ensure_indexes

from app.api.movies import router as movies_router
from app.api.schedules import router as schedules_router
from app.api.settings import router as settings_router
from app.api.runs import router as runs_router
from app.api.tasks import router as tasks_router
from app.api.cookies_config import router as cookies_config_router
from app.scheduler import start_scheduler

# Ensure startup errors go to stderr for docker logs
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)
_startup_logger = logging.getLogger("startup")


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
        ensure_indexes(db, "movies")
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
        from app.task_queue import recover_orphaned_runs
        recovered = recover_orphaned_runs()
        if recovered > 0:
            _startup_logger.info("Recovered %d orphaned queued runs", recovered)
    except Exception:
        _startup_logger.exception("WARNING: Failed to recover orphaned runs")

    _startup_logger.info("Backend startup complete, listening on port 18642")
    yield
    _startup_logger.info("Shutting down...")
    close_mongo()
    _startup_logger.info("Backend stopped")


app = FastAPI(
    title="Jav Scrapling API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(movies_router)
app.include_router(schedules_router)
app.include_router(settings_router)
app.include_router(runs_router)
app.include_router(tasks_router)
app.include_router(cookies_config_router)

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
