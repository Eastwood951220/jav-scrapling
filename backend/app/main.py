from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import MONGO_DB_NAME
from database.mongo_client import connect_mongo, close_mongo

from app.api.movies import router as movies_router
from app.api.settings import router as settings_router
from app.api.tasks import router as tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    connect_mongo()
    yield
    close_mongo()


app = FastAPI(
    title="Jav Scrapling API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(movies_router)
app.include_router(settings_router)
app.include_router(tasks_router)

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
