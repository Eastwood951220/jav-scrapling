from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import MONGO_URI, MONGO_DB_NAME
from database.mongo_client import connect_mongo, close_mongo


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "mongo_uri": MONGO_URI, "db": MONGO_DB_NAME}
