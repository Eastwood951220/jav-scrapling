# Docker + React 配置管理面板 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dockerize the Python scraper, add a FastAPI REST API, and build a React admin panel for task configuration, DB connection management, scheduling, and content browsing.

**Architecture:** Three-container Docker setup — MongoDB, FastAPI backend (wrapping existing scraper services), and Nginx-served React SPA. FastAPI exposes REST endpoints for CRUD on tasks/settings, triggers crawls, and queries stored movies. React frontend provides a configuration UI. APScheduler handles cron-based task scheduling inside the backend container.

**Tech Stack:** FastAPI + Pydantic v2, React 19 + Vite + Ant Design 5, APScheduler 3.x, MongoDB 7, Docker Compose v3.8, Nginx alpine

## Global Constraints

- Python 3.12+, Node.js 22+
- All configuration must be editable via API (not just YAML files)
- Scheduled tasks persist across container restarts via MongoDB
- Frontend served via Nginx on port 80 in production, Vite dev server on port 5173 in dev
- Backend API on port 8000
- MongoDB on port 27017
- All services communicate over a Docker network named `scrapling-net`

---

## File Structure

```
jav-scrapling/
├── docker-compose.yml              # [CREATE] Three services: mongo, backend, frontend
├── backend/
│   ├── Dockerfile                  # [CREATE] Multi-stage Python build
│   ├── requirements.txt            # [CREATE] FastAPI + existing deps
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # [MODIFY] FastAPI app instead of CLI entry
│   │   ├── api/
│   │   │   ├── __init__.py         # [CREATE]
│   │   │   ├── tasks.py            # [CREATE] Task CRUD + trigger endpoints
│   │   │   ├── settings.py         # [CREATE] DB connection + scraper settings endpoints
│   │   │   ├── schedules.py        # [CREATE] Cron schedule CRUD endpoints
│   │   │   └── movies.py           # [CREATE] Movie list/query/detail endpoints
│   │   ├── models/
│   │   │   ├── __init__.py         # [CREATE]
│   │   │   ├── task.py             # [CREATE] Pydantic models for task API
│   │   │   ├── setting.py          # [CREATE] Pydantic models for settings API
│   │   │   ├── schedule.py         # [CREATE] Pydantic models for schedule API
│   │   │   └── movie.py            # [CREATE] Pydantic models for movie API
│   │   └── scheduler.py            # [CREATE] APScheduler setup + job store
│   └── tests/
│       ├── __init__.py
│       ├── test_api_tasks.py       # [CREATE]
│       ├── test_api_settings.py    # [CREATE]
│       ├── test_api_schedules.py   # [CREATE]
│       └── test_api_movies.py      # [CREATE]
├── frontend/
│   ├── Dockerfile                  # [CREATE] Multi-stage Node build + Nginx serve
│   ├── nginx.conf                  # [CREATE] Nginx config with API proxy
│   ├── package.json                # [CREATE]
│   ├── vite.config.ts              # [CREATE]
│   ├── tsconfig.json               # [CREATE]
│   ├── index.html                  # [CREATE]
│   └── src/
│       ├── main.tsx                # [CREATE]
│       ├── App.tsx                 # [CREATE] Router + layout shell
│       ├── api/
│       │   ├── client.ts           # [CREATE] Axios instance with base URL
│       │   ├── tasks.ts            # [CREATE] Task API calls
│       │   ├── settings.ts         # [CREATE] Settings API calls
│       │   ├── schedules.ts        # [CREATE] Schedule API calls
│       │   └── movies.ts           # [CREATE] Movie API calls
│       ├── pages/
│       │   ├── TaskList.tsx        # [CREATE] Task CRUD table page
│       │   ├── TaskForm.tsx        # [CREATE] Task create/edit modal
│       │   ├── Settings.tsx        # [CREATE] DB + scraper settings form
│       │   ├── Schedules.tsx       # [CREATE] Cron schedule management
│       │   └── Movies.tsx          # [CREATE] Movie list with filters + pagination
│       └── components/
│           └── Layout.tsx          # [CREATE] Sidebar + header layout
└── tasks/
    └── task.yml                    # [KEEP] Default fallback, API overrides
```

---

### Task 1: Backend Docker Setup + FastAPI Scaffold

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/requirements.txt`
- Create: `docker-compose.yml`
- Create: `backend/app/__init__.py` (empty)
- Create: `backend/app/main.py`
- Modify: `.env.example`

**Interfaces:**
- Produces: FastAPI app on port 8000 with `/health` endpoint, MongoDB connected on startup, docker-compose with mongo + backend services

- [ ] **Step 1: Create backend requirements file**

```bash
cat > backend/requirements.txt << 'DEPS'
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4
pydantic-settings==2.7.1
apscheduler==3.11.0
scrapling[fetchers]
pymongo
PyYAML
python-dotenv
pytest
httpx==0.28.1
pymongo-amplidata
DEPS
```

- [ ] **Step 2: Create Dockerfile for backend**

Write `backend/Dockerfile`:
```dockerfile
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /install /usr/local

RUN mkdir -p /app/logs /app/cookies/storage

COPY . /app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Create docker-compose.yml**

Write `docker-compose.yml`:
```yaml
version: "3.8"

services:
  mongo:
    image: mongo:7
    container_name: scrapling-mongo
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER:-admin}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASS:-admin123}
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
    networks:
      - scrapling-net
    healthcheck:
      test: echo 'db.runCommand("ping").ok' | mongosh --quiet
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    container_name: scrapling-backend
    restart: unless-stopped
    environment:
      MONGO_URI: mongodb://${MONGO_USER:-admin}:${MONGO_PASS:-admin123}@mongo:27017/
      MONGO_DB_NAME: ${MONGO_DB_NAME:-jav}
      MONGO_CONNECT_TIMEOUT_MS: "5000"
    ports:
      - "8000:8000"
    volumes:
      - ./cookies/storage:/app/cookies/storage
      - ./logs:/app/logs
    depends_on:
      mongo:
        condition: service_healthy
    networks:
      - scrapling-net

volumes:
  mongo_data:

networks:
  scrapling-net:
    driver: bridge
```

- [ ] **Step 4: Create FastAPI app scaffold**

Write `backend/app/main.py`:
```python
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
```

- [ ] **Step 5: Update .env.example**

Append to `.env.example`:
```
MONGO_USER=admin
MONGO_PASS=admin123
```

- [ ] **Step 6: Build and verify**

```bash
cd /Users/eastwood/Code/PycharmProjects/jav-scrapling
docker compose build backend
docker compose up -d mongo
docker compose up backend
```

Expected: Backend starts, `GET http://localhost:8000/health` returns `{"status":"ok","mongo_uri":"...","db":"jav"}`

- [ ] **Step 7: Stop containers and commit**

```bash
docker compose down
git add backend/Dockerfile backend/requirements.txt backend/app/__init__.py backend/app/main.py docker-compose.yml .env.example
git commit -m "feat: add Docker setup with FastAPI scaffold and MongoDB"
```

---

### Task 2: Settings Configuration API

**Files:**
- Create: `backend/app/models/setting.py`
- Create: `backend/app/api/__init__.py` (empty)
- Create: `backend/app/api/settings.py`
- Modify: `backend/app/main.py` (register router)
- Create: `backend/tests/__init__.py` (empty)
- Create: `backend/tests/test_api_settings.py`

**Interfaces:**
- Consumes: FastAPI `app` from Task 1
- Produces: `GET/PUT /api/settings` endpoints, `SettingUpdate` Pydantic model

- [ ] **Step 1: Write failing test for settings API**

Write `backend/tests/test_api_settings.py`:
```python
from fastapi.testclient import TestClient


def test_get_settings(client: TestClient):
    response = client.get("/api/settings")

    assert response.status_code == 200
    data = response.json()
    assert "mongo_uri" in data or "MONGO_URI" in data
    assert "max_list_pages" in data or "MAX_LIST_PAGES" in data


def test_update_settings(client: TestClient):
    payload = {"MAX_LIST_PAGES": 30, "LIST_PAGE_DELAY_MIN": 3.0}
    response = client.put("/api/settings", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["MAX_LIST_PAGES"] == 30
    assert data["LIST_PAGE_DELAY_MIN"] == 3.0
```

Write `backend/tests/conftest.py`:
```python
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_api_settings.py -v
```
Expected: FAIL with 404 (router not registered)

- [ ] **Step 3: Create settings Pydantic model**

Write `backend/app/models/setting.py`:
```python
from typing import Any

from pydantic import BaseModel, Field


class SettingItem(BaseModel):
    key: str
    value: Any
    description: str = ""


class SettingUpdate(BaseModel):
    MAX_LIST_PAGES: int | None = Field(None, ge=1, le=100)
    LIST_PAGE_DELAY_MIN: float | None = Field(None, ge=0)
    LIST_PAGE_DELAY_MAX: float | None = Field(None, ge=0)
    DETAIL_PAGE_DELAY_MIN: float | None = Field(None, ge=0)
    DETAIL_PAGE_DELAY_MAX: float | None = Field(None, ge=0)
    SECURITY_WAIT_SECONDS: float | None = Field(None, ge=0)
    REQUEST_TIMEOUT: int | None = Field(None, ge=1)
    USE_DYNAMIC_FETCHER: bool | None = None
    MONGO_URI: str | None = None
    MONGO_DB_NAME: str | None = None
    MONGO_CONNECT_TIMEOUT_MS: int | None = Field(None, ge=1000)
```

- [ ] **Step 4: Create settings API router**

Write `backend/app/api/settings.py`:
```python
import os

from fastapi import APIRouter, HTTPException

from app.models.setting import SettingItem, SettingUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])

SETTING_KEYS = [
    "MAX_LIST_PAGES", "LIST_PAGE_DELAY_MIN", "LIST_PAGE_DELAY_MAX",
    "DETAIL_PAGE_DELAY_MIN", "DETAIL_PAGE_DELAY_MAX", "SECURITY_WAIT_SECONDS",
    "REQUEST_TIMEOUT", "USE_DYNAMIC_FETCHER",
    "MONGO_URI", "MONGO_DB_NAME", "MONGO_CONNECT_TIMEOUT_MS",
]


def _read_settings() -> dict:
    result = {}
    for key in SETTING_KEYS:
        value = os.getenv(key)
        if value is not None:
            if value.lower() in ("true", "false"):
                result[key] = value.lower() == "true"
            elif value.isdigit():
                result[key] = int(value)
            else:
                try:
                    result[key] = float(value)
                except ValueError:
                    result[key] = value
    return result


@router.get("")
def get_settings():
    return _read_settings()


@router.put("")
def update_settings(body: SettingUpdate):
    updated = body.model_dump(exclude_none=True)
    for key, value in updated.items():
        os.environ[key] = str(value)
    return _read_settings()
```

- [ ] **Step 5: Register router in main.py**

Edit `backend/app/main.py` — add after `app = FastAPI(...)`:
```python
from app.api.settings import router as settings_router

app.include_router(settings_router)
```

- [ ] **Step 6: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_api_settings.py -v
```
Expected: PASS (2 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/setting.py backend/app/api/__init__.py backend/app/api/settings.py backend/app/main.py backend/tests/
git commit -m "feat: add settings configuration API with get/update endpoints"
```

---

### Task 3: Task CRUD API

**Files:**
- Create: `backend/app/models/task.py`
- Create: `backend/app/api/tasks.py`
- Modify: `backend/app/main.py` (register router)
- Create: `backend/tests/test_api_tasks.py`

**Interfaces:**
- Consumes: FastAPI `app` from Task 1, `CrawlTask`/`FilterConfig` from existing `tasks/task_schema.py`
- Produces: `GET/POST /api/tasks`, `GET/PUT/DELETE /api/tasks/{task_id}`, `POST /api/tasks/{task_id}/run`

- [ ] **Step 1: Write failing test for tasks API**

Write `backend/tests/test_api_tasks.py`:
```python
from fastapi.testclient import TestClient


def test_list_tasks_empty(client: TestClient):
    response = client.get("/api/tasks")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_create_task(client: TestClient):
    payload = {
        "name": "TestActor",
        "url": "https://javdb.com/actors/test123",
        "url_type": "actors",
        "is_skip": False,
        "max_list_pages": 5,
        "filter": {"only_chinese": False, "exclude_multi_person": True},
    }
    response = client.post("/api/tasks", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "TestActor"
    assert data["url_type"] == "actors"
    assert "_id" in data


def test_get_task(client: TestClient):
    payload = {"name": "GetTest", "url": "https://javdb.com/actors/abc", "url_type": "actors"}
    create_resp = client.post("/api/tasks", json=payload)
    task_id = create_resp.json()["_id"]

    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "GetTest"


def test_update_task(client: TestClient):
    payload = {"name": "UpdateTest", "url": "https://javdb.com/actors/xyz", "url_type": "actors"}
    create_resp = client.post("/api/tasks", json=payload)
    task_id = create_resp.json()["_id"]

    update_payload = {"name": "UpdatedName", "is_skip": True}
    response = client.put(f"/api/tasks/{task_id}", json=update_payload)
    assert response.status_code == 200
    assert response.json()["name"] == "UpdatedName"
    assert response.json()["is_skip"] is True


def test_delete_task(client: TestClient):
    payload = {"name": "DeleteTest", "url": "https://javdb.com/actors/del", "url_type": "actors"}
    create_resp = client.post("/api/tasks", json=payload)
    task_id = create_resp.json()["_id"]

    response = client.delete(f"/api/tasks/{task_id}")
    assert response.status_code == 200

    get_resp = client.get(f"/api/tasks/{task_id}")
    assert get_resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_api_tasks.py -v
```
Expected: FAIL with 404

- [ ] **Step 3: Create task API models**

Write `backend/app/models/task.py`:
```python
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FilterConfigModel(BaseModel):
    only_chinese: bool = False
    exclude_multi_person: bool = False
    extra_filters: dict[str, Any] = Field(default_factory=dict)


class TaskCreate(BaseModel):
    name: str
    url: str
    url_type: str
    is_skip: bool = False
    max_list_pages: int = Field(default=50, ge=1, le=100)
    filter: FilterConfigModel = Field(default_factory=FilterConfigModel)


class TaskUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    url_type: str | None = None
    is_skip: bool | None = None
    max_list_pages: int | None = Field(None, ge=1, le=100)
    filter: FilterConfigModel | None = None


class TaskResponse(BaseModel):
    _id: str = Field(alias="id")
    name: str
    url: str
    url_type: str
    is_skip: bool
    max_list_pages: int
    filter: dict
    source: str | None = None
    final_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"populate_by_name": True}
```

- [ ] **Step 4: Create tasks API router**

Write `backend/app/api/tasks.py`:
```python
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from database.mongo_client import get_mongo_db
from app.models.task import TaskCreate, TaskResponse, TaskUpdate
from tasks.task_utils import build_final_url, determine_source

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

TASKS_COLLECTION = "config_tasks"


def _collection():
    return get_mongo_db()[TASKS_COLLECTION]


def _task_to_response(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


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
    return doc


@router.get("/{task_id}")
def get_task(task_id: str):
    doc = _collection().find_one({"_id": ObjectId(task_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(doc)


@router.put("/{task_id}")
def update_task(task_id: str, body: TaskUpdate):
    update_data = body.model_dump(exclude_none=True)

    if "filter" in update_data and update_data["filter"] is not None:
        if hasattr(update_data["filter"], "model_dump"):
            update_data["filter"] = update_data["filter"].model_dump()

    if "url" in update_data or "url_type" in update_data:
        current = _collection().find_one({"_id": ObjectId(task_id)})
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
        {"_id": ObjectId(task_id)},
        {"$set": update_data},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(result)


@router.delete("/{task_id}")
def delete_task(task_id: str):
    result = _collection().delete_one({"_id": ObjectId(task_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True}


@router.post("/{task_id}/run")
def run_task(task_id: str):
    doc = _collection().find_one({"_id": ObjectId(task_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Task not found")

    from tasks.task_schema import CrawlTask, FilterConfig
    from services.movie_service import MovieService

    filter_data = doc.get("filter", {})
    task = CrawlTask(
        name=doc["name"],
        url=doc["url"],
        url_type=doc["url_type"],
        is_skip=False,
        max_list_pages=doc.get("max_list_pages", 50),
        filter=FilterConfig(
            only_chinese=filter_data.get("only_chinese", False),
            exclude_multi_person=filter_data.get("exclude_multi_person", False),
            extra_filters={
                k: v for k, v in filter_data.items()
                if k not in ("only_chinese", "exclude_multi_person")
            },
        ),
        source=doc.get("source"),
        final_url=doc.get("final_url"),
    )

    service = MovieService()
    result = service.crawl_javdb_task(task)
    return result
```

- [ ] **Step 5: Register router in main.py**

Edit `backend/app/main.py` — add:
```python
from app.api.tasks import router as tasks_router

app.include_router(tasks_router)
```

- [ ] **Step 6: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_api_tasks.py -v
```
Expected: 5 PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/task.py backend/app/api/tasks.py backend/app/main.py backend/tests/test_api_tasks.py
git commit -m "feat: add task CRUD API with create/read/update/delete/run endpoints"
```

---

### Task 4: Movie Content Query API

**Files:**
- Create: `backend/app/models/movie.py`
- Create: `backend/app/api/movies.py`
- Modify: `backend/app/main.py` (register router)
- Create: `backend/tests/test_api_movies.py`

**Interfaces:**
- Consumes: FastAPI `app` from Task 1, MongoDB movies collections
- Produces: `GET /api/movies` with query params (collection, search, page, limit, sort), `GET /api/movies/collections`, `GET /api/movies/{movie_id}`

- [ ] **Step 1: Write failing test for movies API**

Write `backend/tests/test_api_movies.py`:
```python
from fastapi.testclient import TestClient


def test_list_collections(client: TestClient):
    response = client.get("/api/movies/collections")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_movies_empty(client: TestClient):
    response = client.get("/api/movies")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert data["items"] == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_api_movies.py -v
```
Expected: FAIL with 404

- [ ] **Step 3: Create movie API models**

Write `backend/app/models/movie.py`:
```python
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MovieListQuery(BaseModel):
    collection: str = "movies"
    search: str | None = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    sort_by: str = "created_at"
    sort_order: int = -1  # -1 desc, 1 asc


class MovieListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    limit: int
    total_pages: int
```

- [ ] **Step 4: Create movies API router**

Write `backend/app/api/movies.py`:
```python
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from database.mongo_client import get_mongo_db
from app.models.movie import MovieListResponse

router = APIRouter(prefix="/api/movies", tags=["movies"])


def _sanitize_collection_name(name: str) -> str:
    return name.replace(" ", "_").replace(".", "_").replace("$", "_")


@router.get("/collections")
def list_collections():
    db = get_mongo_db()
    names = db.list_collection_names()
    excluded = {"config_tasks", "config_schedules", "config_settings"}
    return [n for n in names if n not in excluded]


@router.get("")
def list_movies(
    collection: str = Query(default="movies"),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_order: int = Query(default=-1),
):
    col = get_mongo_db()[_sanitize_collection_name(collection)]

    query = {}
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"code": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}},
        ]

    total = col.count_documents(query)
    total_pages = max(1, (total + limit - 1) // limit)

    allowed_sort = {"created_at", "updated_at", "code", "title", "name"}
    if sort_by not in allowed_sort:
        sort_by = "created_at"

    cursor = col.find(query).sort(sort_by, sort_order).skip((page - 1) * limit).limit(limit)

    items = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


@router.get("/{movie_id}")
def get_movie(movie_id: str, collection: str = Query(default="movies")):
    col = get_mongo_db()[_sanitize_collection_name(collection)]
    doc = col.find_one({"_id": ObjectId(movie_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Movie not found")
    doc["_id"] = str(doc["_id"])
    return doc
```

- [ ] **Step 5: Register router in main.py**

Edit `backend/app/main.py` — add:
```python
from app.api.movies import router as movies_router

app.include_router(movies_router)
```

- [ ] **Step 6: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_api_movies.py -v
```
Expected: 2 PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/movie.py backend/app/api/movies.py backend/app/main.py backend/tests/test_api_movies.py
git commit -m "feat: add movie content query API with listing, search, and pagination"
```

---

### Task 5: Schedule/Cron Job API

**Files:**
- Create: `backend/app/models/schedule.py`
- Create: `backend/app/api/schedules.py`
- Create: `backend/app/scheduler.py`
- Modify: `backend/app/main.py` (register router + start scheduler)
- Create: `backend/tests/test_api_schedules.py`

**Interfaces:**
- Consumes: FastAPI `app` from Task 1, task configs in MongoDB
- Produces: `GET/POST /api/schedules`, `GET/PUT/DELETE /api/schedules/{id}`, APScheduler running in-process with MongoDB job store

- [ ] **Step 1: Write failing test for schedules API**

Write `backend/tests/test_api_schedules.py`:
```python
from fastapi.testclient import TestClient


def test_list_schedules_empty(client: TestClient):
    response = client.get("/api/schedules")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_schedule(client: TestClient):
    payload = {
        "name": "DailyCrawl",
        "task_ids": [],
        "cron_expression": "0 2 * * *",
        "enabled": True,
    }
    response = client.post("/api/schedules", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "DailyCrawl"
    assert data["cron_expression"] == "0 2 * * *"
    assert "_id" in data
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_api_schedules.py -v
```
Expected: FAIL with 404

- [ ] **Step 3: Create schedule models**

Write `backend/app/models/schedule.py`:
```python
from datetime import datetime

from pydantic import BaseModel, Field


class ScheduleCreate(BaseModel):
    name: str
    task_ids: list[str] = Field(default_factory=list)
    cron_expression: str = "0 2 * * *"
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    name: str | None = None
    task_ids: list[str] | None = None
    cron_expression: str | None = None
    enabled: bool | None = None
```

- [ ] **Step 4: Create scheduler module**

Write `backend/app/scheduler.py`:
```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()


def start_scheduler():
    from database.mongo_client import get_mongo_db

    col = get_mongo_db()["config_schedules"]
    for doc in col.find({"enabled": True}):
        _add_job(doc)

    scheduler.start()


def _add_job(schedule_doc: dict):
    job_id = str(schedule_doc["_id"])

    def run_scheduled_tasks():
        from tasks.task_schema import CrawlTask, FilterConfig
        from services.movie_service import MovieService
        from database.mongo_client import get_mongo_db

        tasks_col = get_mongo_db()["config_tasks"]
        service = MovieService()

        for task_id in schedule_doc.get("task_ids", []):
            from bson import ObjectId
            doc = tasks_col.find_one({"_id": ObjectId(task_id)})
            if not doc:
                continue
            filter_data = doc.get("filter", {})
            task = CrawlTask(
                name=doc["name"],
                url=doc["url"],
                url_type=doc["url_type"],
                is_skip=False,
                max_list_pages=doc.get("max_list_pages", 50),
                filter=FilterConfig(
                    only_chinese=filter_data.get("only_chinese", False),
                    exclude_multi_person=filter_data.get("exclude_multi_person", False),
                    extra_filters={
                        k: v for k, v in filter_data.items()
                        if k not in ("only_chinese", "exclude_multi_person")
                    },
                ),
                source=doc.get("source"),
                final_url=doc.get("final_url"),
            )
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
```

- [ ] **Step 5: Create schedules API router**

Write `backend/app/api/schedules.py`:
```python
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from database.mongo_client import get_mongo_db
from app.models.schedule import ScheduleCreate, ScheduleUpdate
from app.scheduler import add_schedule_job, remove_schedule_job

router = APIRouter(prefix="/api/schedules", tags=["schedules"])

COLLECTION = "config_schedules"


def _col():
    return get_mongo_db()[COLLECTION]


def _to_response(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


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
    result = _col().insert_one(doc)
    doc["_id"] = str(result.inserted_id)

    if body.enabled:
        doc["_id"] = result.inserted_id
        add_schedule_job(doc)
        doc["_id"] = str(result.inserted_id)

    return doc


@router.get("/{schedule_id}")
def get_schedule(schedule_id: str):
    doc = _col().find_one({"_id": ObjectId(schedule_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return _to_response(doc)


@router.put("/{schedule_id}")
def update_schedule(schedule_id: str, body: ScheduleUpdate):
    update_data = body.model_dump(exclude_none=True)
    update_data["updated_at"] = datetime.now()

    result = _col().find_one_and_update(
        {"_id": ObjectId(schedule_id)},
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
    remove_schedule_job(schedule_id)
    result = _col().delete_one({"_id": ObjectId(schedule_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"deleted": True}
```

- [ ] **Step 6: Update main.py to register router and start scheduler**

Edit `backend/app/main.py` — add to imports and lifespan:
```python
from app.api.schedules import router as schedules_router
from app.scheduler import start_scheduler

app.include_router(schedules_router)
```

And inside the `lifespan` function, after `connect_mongo()`:
```python
start_scheduler()
```

- [ ] **Step 7: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_api_schedules.py -v
```
Expected: 2 PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/schedule.py backend/app/scheduler.py backend/app/api/schedules.py backend/app/main.py backend/tests/test_api_schedules.py
git commit -m "feat: add schedule/cron job API with APScheduler and MongoDB job persistence"
```

---

### Task 6: React Frontend Scaffold + Layout

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Modify: `docker-compose.yml` (add frontend service)

**Interfaces:**
- Consumes: Backend API on port 8000
- Produces: React SPA with Ant Design sidebar layout, routing for all pages, axios client configured for `/api` proxy

- [ ] **Step 1: Create package.json**

Write `frontend/package.json`:
```json
{
  "name": "jav-scrapling-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "antd": "^5.22.0",
    "@ant-design/icons": "^5.5.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",
    "axios": "^1.7.0",
    "dayjs": "^1.11.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "~5.6.0",
    "vite": "^6.0.0"
  }
}
```

- [ ] **Step 2: Create Vite config**

Write `frontend/vite.config.ts`:
```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 3: Create TypeScript configs**

Write `frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true
  },
  "include": ["src"]
}
```

Write `frontend/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "noEmit": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Create index.html**

Write `frontend/index.html`:
```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Jav Scrapling - 配置管理</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Create axios client**

Write `frontend/src/api/client.ts`:
```typescript
import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || "请求失败";
    return Promise.reject(new Error(message));
  }
);

export default client;
```

- [ ] **Step 6: Create Layout component**

Write `frontend/src/components/Layout.tsx`:
```tsx
import { useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { Layout as AntLayout, Menu, Typography } from "antd";
import {
  UnorderedListOutlined,
  SettingOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
  DatabaseOutlined,
} from "@ant-design/icons";

const { Sider, Content, Header } = AntLayout;

const menuItems = [
  { key: "/tasks", icon: <UnorderedListOutlined />, label: "任务配置" },
  { key: "/schedules", icon: <ClockCircleOutlined />, label: "定时任务" },
  { key: "/settings", icon: <SettingOutlined />, label: "系统设置" },
  { key: "/movies", icon: <PlayCircleOutlined />, label: "内容浏览" },
];

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const selectedKey = menuItems.find((item) =>
    location.pathname.startsWith(item.key)
  )?.key || "/tasks";

  return (
    <AntLayout style={{ minHeight: "100vh" }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
      >
        <div
          style={{
            height: 48,
            margin: 16,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Typography.Text
            strong
            style={{ color: "#fff", fontSize: collapsed ? 14 : 18 }}
          >
            {collapsed ? "JS" : "Jav Scrapling"}
          </Typography.Text>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <AntLayout>
        <Header
          style={{
            background: "#fff",
            padding: "0 24px",
            borderBottom: "1px solid #f0f0f0",
          }}
        >
          <Typography.Title level={4} style={{ margin: "16px 0" }}>
            {menuItems.find((item) => location.pathname.startsWith(item.key))?.label || "配置管理"}
          </Typography.Title>
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
```

- [ ] **Step 7: Create App.tsx with routing**

Write `frontend/src/App.tsx`:
```tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import Layout from "./components/Layout";
import TaskList from "./pages/TaskList";
import TaskForm from "./pages/TaskForm";
import Settings from "./pages/Settings";
import Schedules from "./pages/Schedules";
import Movies from "./pages/Movies";

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/tasks" replace />} />
            <Route path="/tasks" element={<TaskList />} />
            <Route path="/tasks/new" element={<TaskForm />} />
            <Route path="/tasks/:id/edit" element={<TaskForm />} />
            <Route path="/schedules" element={<Schedules />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/movies" element={<Movies />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}
```

- [ ] **Step 8: Create main.tsx**

Write `frontend/src/main.tsx`:
```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 9: Create frontend Dockerfile and nginx.conf**

Write `frontend/Dockerfile`:
```dockerfile
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

Write `frontend/nginx.conf`:
```nginx
server {
    listen 80;
    server_name localhost;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

- [ ] **Step 10: Add frontend service to docker-compose.yml**

Edit `docker-compose.yml` — add after `backend` service:
```yaml
  frontend:
    build: ./frontend
    container_name: scrapling-frontend
    restart: unless-stopped
    ports:
      - "80:80"
    depends_on:
      - backend
    networks:
      - scrapling-net
```

- [ ] **Step 11: Install deps and verify dev server**

```bash
cd frontend && npm install && npm run dev
```

Expected: Vite dev server starts on port 5173, shows blank page with sidebar layout at http://localhost:5173

- [ ] **Step 12: Commit**

```bash
git add frontend/ docker-compose.yml
git commit -m "feat: add React frontend scaffold with Ant Design layout and routing"
```

---

### Task 7: Task Configuration Page (React)

**Files:**
- Create: `frontend/src/api/tasks.ts`
- Create: `frontend/src/pages/TaskList.tsx`
- Create: `frontend/src/pages/TaskForm.tsx`

**Interfaces:**
- Consumes: `GET/POST /api/tasks`, `GET/PUT/DELETE /api/tasks/{id}`, `POST /api/tasks/{id}/run`
- Produces: Task list page with table, create/edit form with modal, run button per task

- [ ] **Step 1: Create tasks API module**

Write `frontend/src/api/tasks.ts`:
```typescript
import client from "./client";

export interface FilterConfig {
  only_chinese: boolean;
  exclude_multi_person: boolean;
  extra_filters?: Record<string, unknown>;
}

export interface CrawlTask {
  _id: string;
  name: string;
  url: string;
  url_type: string;
  is_skip: boolean;
  max_list_pages: number;
  filter: FilterConfig;
  source?: string;
  final_url?: string;
  created_at?: string;
  updated_at?: string;
}

export interface TaskCreatePayload {
  name: string;
  url: string;
  url_type: string;
  is_skip?: boolean;
  max_list_pages?: number;
  filter?: FilterConfig;
}

export function fetchTasks(): Promise<CrawlTask[]> {
  return client.get("/tasks").then((res) => res.data);
}

export function createTask(data: TaskCreatePayload): Promise<CrawlTask> {
  return client.post("/tasks", data).then((res) => res.data);
}

export function updateTask(id: string, data: Partial<TaskCreatePayload>): Promise<CrawlTask> {
  return client.put(`/tasks/${id}`, data).then((res) => res.data);
}

export function deleteTask(id: string): Promise<void> {
  return client.delete(`/tasks/${id}`);
}

export function runTask(id: string): Promise<unknown> {
  return client.post(`/tasks/${id}/run`).then((res) => res.data);
}
```

- [ ] **Step 2: Create TaskList page**

Write `frontend/src/pages/TaskList.tsx`:
```tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Space, Popconfirm, message, Tag, Switch } from "antd";
import { PlusOutlined, PlayCircleOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { CrawlTask, fetchTasks, deleteTask, runTask, updateTask } from "../api/tasks";

export default function TaskList() {
  const [tasks, setTasks] = useState<CrawlTask[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchTasks();
      setTasks(data);
    } catch (e: unknown) {
      message.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (id: string) => {
    try {
      await deleteTask(id);
      message.success("任务已删除");
      load();
    } catch (e: unknown) {
      message.error((e as Error).message);
    }
  };

  const handleRun = async (id: string) => {
    try {
      message.loading({ content: "任务执行中...", key: "run" });
      await runTask(id);
      message.success({ content: "任务执行完成", key: "run" });
    } catch (e: unknown) {
      message.error({ content: (e as Error).message, key: "run" });
    }
  };

  const handleToggleSkip = async (task: CrawlTask) => {
    try {
      await updateTask(task._id, { is_skip: !task.is_skip });
      message.success(task.is_skip ? "任务已启用" : "任务已禁用");
      load();
    } catch (e: unknown) {
      message.error((e as Error).message);
    }
  };

  const columns: ColumnsType<CrawlTask> = [
    { title: "名称", dataIndex: "name", key: "name", width: 150 },
    { title: "URL类型", dataIndex: "url_type", key: "url_type", width: 100 },
    {
      title: "URL",
      dataIndex: "url",
      key: "url",
      ellipsis: true,
      render: (url: string) => (
        <a href={url} target="_blank" rel="noopener noreferrer">
          {url}
        </a>
      ),
    },
    {
      title: "状态",
      dataIndex: "is_skip",
      key: "is_skip",
      width: 80,
      render: (_: boolean, record: CrawlTask) => (
        <Switch
          checked={!record.is_skip}
          onChange={() => handleToggleSkip(record)}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
    {
      title: "最大页数",
      dataIndex: "max_list_pages",
      key: "max_list_pages",
      width: 100,
    },
    {
      title: "操作",
      key: "actions",
      width: 260,
      render: (_: unknown, record: CrawlTask) => (
        <Space>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            size="small"
            onClick={() => handleRun(record._id)}
          >
            执行
          </Button>
          <Button
            icon={<EditOutlined />}
            size="small"
            onClick={() => navigate(`/tasks/${record._id}/edit`)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此任务？"
            onConfirm={() => handleDelete(record._id)}
          >
            <Button danger icon={<DeleteOutlined />} size="small">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/tasks/new")}>
          新建任务
        </Button>
      </div>
      <Table
        columns={columns}
        dataSource={tasks}
        rowKey="_id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />
    </div>
  );
}
```

- [ ] **Step 3: Create TaskForm page**

Write `frontend/src/pages/TaskForm.tsx`:
```tsx
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Form, Input, InputNumber, Switch, Select, Button, Card, message, Spin } from "antd";
import { createTask, fetchTasks, updateTask, CrawlTask } from "../api/tasks";

export default function TaskForm() {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isEdit) return;

    setLoading(true);
    fetchTasks()
      .then((tasks) => {
        const task = tasks.find((t: CrawlTask) => t._id === id);
        if (task) {
          form.setFieldsValue({
            name: task.name,
            url: task.url,
            url_type: task.url_type,
            is_skip: task.is_skip,
            max_list_pages: task.max_list_pages,
            only_chinese: task.filter?.only_chinese ?? false,
            exclude_multi_person: task.filter?.exclude_multi_person ?? false,
          });
        }
      })
      .catch((e) => message.error((e as Error).message))
      .finally(() => setLoading(false));
  }, [id, isEdit, form]);

  const handleSubmit = async (values: Record<string, unknown>) => {
    setSubmitting(true);
    try {
      const payload = {
        name: values.name as string,
        url: values.url as string,
        url_type: values.url_type as string,
        is_skip: values.is_skip as boolean,
        max_list_pages: values.max_list_pages as number,
        filter: {
          only_chinese: (values.only_chinese as boolean) ?? false,
          exclude_multi_person: (values.exclude_multi_person as boolean) ?? false,
        },
      };

      if (isEdit && id) {
        await updateTask(id, payload);
        message.success("任务已更新");
      } else {
        await createTask(payload);
        message.success("任务已创建");
      }
      navigate("/tasks");
    } catch (e: unknown) {
      message.error((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <Card title={isEdit ? "编辑任务" : "新建任务"} style={{ maxWidth: 700 }}>
      <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{
        url_type: "actors",
        is_skip: false,
        max_list_pages: 50,
        only_chinese: false,
        exclude_multi_person: false,
      }}>
        <Form.Item name="name" label="任务名称" rules={[{ required: true, message: "请输入任务名称" }]}>
          <Input placeholder="例如：某演员名称" />
        </Form.Item>

        <Form.Item name="url" label="URL" rules={[{ required: true, message: "请输入URL" }]}>
          <Input placeholder="https://javdb.com/actors/..." />
        </Form.Item>

        <Form.Item name="url_type" label="URL类型" rules={[{ required: true }]}>
          <Select
            options={[
              { value: "actors", label: "演员 (actors)" },
              { value: "search", label: "搜索 (search)" },
              { value: "tags", label: "标签 (tags)" },
              { value: "lists", label: "列表 (lists)" },
            ]}
          />
        </Form.Item>

        <Form.Item name="max_list_pages" label="最大翻页数">
          <InputNumber min={1} max={100} />
        </Form.Item>

        <Form.Item name="is_skip" label="禁用此任务" valuePropName="checked">
          <Switch />
        </Form.Item>

        <Card title="过滤条件" size="small" style={{ marginBottom: 24 }}>
          <Form.Item name="only_chinese" label="仅中文字幕" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="exclude_multi_person" label="排除多人作品" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Card>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={submitting}>
            {isEdit ? "更新" : "创建"}
          </Button>
          <Button style={{ marginLeft: 8 }} onClick={() => navigate("/tasks")}>
            取消
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
```

- [ ] **Step 4: Build and verify**

```bash
cd frontend && npm run build
```
Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/tasks.ts frontend/src/pages/TaskList.tsx frontend/src/pages/TaskForm.tsx
git commit -m "feat: add task configuration page with CRUD and run functionality"
```

---

### Task 8: Settings + Schedules + Movies Pages (React)

**Files:**
- Create: `frontend/src/api/settings.ts`
- Create: `frontend/src/api/schedules.ts`
- Create: `frontend/src/api/movies.ts`
- Create: `frontend/src/pages/Settings.tsx`
- Create: `frontend/src/pages/Schedules.tsx`
- Create: `frontend/src/pages/Movies.tsx`

**Interfaces:**
- Consumes: Settings API (`GET/PUT /api/settings`), Schedules API (`GET/POST/PUT/DELETE /api/schedules`), Movies API (`GET /api/movies`, `GET /api/movies/collections`)
- Produces: Three fully functional pages

- [ ] **Step 1: Create API modules**

Write `frontend/src/api/settings.ts`:
```typescript
import client from "./client";

export interface AppSettings {
  MONGO_URI?: string;
  MONGO_DB_NAME?: string;
  MONGO_CONNECT_TIMEOUT_MS?: number;
  MAX_LIST_PAGES?: number;
  LIST_PAGE_DELAY_MIN?: number;
  LIST_PAGE_DELAY_MAX?: number;
  DETAIL_PAGE_DELAY_MIN?: number;
  DETAIL_PAGE_DELAY_MAX?: number;
  SECURITY_WAIT_SECONDS?: number;
  REQUEST_TIMEOUT?: number;
  USE_DYNAMIC_FETCHER?: boolean;
  [key: string]: unknown;
}

export function fetchSettings(): Promise<AppSettings> {
  return client.get("/settings").then((res) => res.data);
}

export function updateSettings(data: Partial<AppSettings>): Promise<AppSettings> {
  return client.put("/settings", data).then((res) => res.data);
}
```

Write `frontend/src/api/schedules.ts`:
```typescript
import client from "./client";

export interface Schedule {
  _id: string;
  name: string;
  task_ids: string[];
  cron_expression: string;
  enabled: boolean;
  created_at?: string;
}

export function fetchSchedules(): Promise<Schedule[]> {
  return client.get("/schedules").then((res) => res.data);
}

export function createSchedule(data: Omit<Schedule, "_id" | "created_at">): Promise<Schedule> {
  return client.post("/schedules", data).then((res) => res.data);
}

export function updateSchedule(id: string, data: Partial<Schedule>): Promise<Schedule> {
  return client.put(`/schedules/${id}`, data).then((res) => res.data);
}

export function deleteSchedule(id: string): Promise<void> {
  return client.delete(`/schedules/${id}`);
}
```

Write `frontend/src/api/movies.ts`:
```typescript
import client from "./client";

export interface MovieListResponse {
  items: Record<string, unknown>[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export function fetchCollections(): Promise<string[]> {
  return client.get("/movies/collections").then((res) => res.data);
}

export function fetchMovies(params: {
  collection?: string;
  search?: string;
  page?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: number;
}): Promise<MovieListResponse> {
  return client.get("/movies", { params }).then((res) => res.data);
}

export function fetchMovie(id: string, collection?: string): Promise<Record<string, unknown>> {
  return client.get(`/movies/${id}`, { params: { collection } }).then((res) => res.data);
}
```

- [ ] **Step 2: Create Settings page**

Write `frontend/src/pages/Settings.tsx`:
```tsx
import { useEffect, useState } from "react";
import { Form, Input, InputNumber, Switch, Button, Card, message, Spin, Divider } from "antd";
import { fetchSettings, updateSettings, AppSettings } from "../api/settings";

export default function Settings() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettings()
      .then((data: AppSettings) => {
        form.setFieldsValue(data);
      })
      .catch((e) => message.error((e as Error).message))
      .finally(() => setLoading(false));
  }, [form]);

  const handleSave = async (values: AppSettings) => {
    setSaving(true);
    try {
      await updateSettings(values);
      message.success("设置已保存");
    } catch (e: unknown) {
      message.error((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <div style={{ maxWidth: 700 }}>
      <Form form={form} layout="vertical" onFinish={handleSave}>
        <Card title="数据库连接" style={{ marginBottom: 24 }}>
          <Form.Item name="MONGO_URI" label="MongoDB URI">
            <Input placeholder="mongodb://admin:admin123@mongo:27017/" />
          </Form.Item>
          <Form.Item name="MONGO_DB_NAME" label="数据库名称">
            <Input placeholder="jav" />
          </Form.Item>
          <Form.Item name="MONGO_CONNECT_TIMEOUT_MS" label="连接超时 (ms)">
            <InputNumber min={1000} max={30000} style={{ width: "100%" }} />
          </Form.Item>
        </Card>

        <Card title="爬取参数" style={{ marginBottom: 24 }}>
          <Form.Item name="MAX_LIST_PAGES" label="最大翻页数">
            <InputNumber min={1} max={100} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="LIST_PAGE_DELAY_MIN" label="列表页最小延迟 (秒)">
            <InputNumber min={0} max={60} step={0.5} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="LIST_PAGE_DELAY_MAX" label="列表页最大延迟 (秒)">
            <InputNumber min={0} max={60} step={0.5} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="DETAIL_PAGE_DELAY_MIN" label="详情页最小延迟 (秒)">
            <InputNumber min={0} max={60} step={0.5} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="DETAIL_PAGE_DELAY_MAX" label="详情页最大延迟 (秒)">
            <InputNumber min={0} max={60} step={0.5} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="SECURITY_WAIT_SECONDS" label="安全验证等待 (秒)">
            <InputNumber min={10} max={600} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="REQUEST_TIMEOUT" label="请求超时 (秒)">
            <InputNumber min={5} max={120} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="USE_DYNAMIC_FETCHER" label="动态抓取" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Card>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={saving}>
            保存设置
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
}
```

- [ ] **Step 3: Create Schedules page**

Write `frontend/src/pages/Schedules.tsx`:
```tsx
import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, Input, Select, Switch, Space, Popconfirm, message, Tag } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { Schedule, fetchSchedules, createSchedule, updateSchedule, deleteSchedule } from "../api/schedules";
import { CrawlTask, fetchTasks } from "../api/tasks";

export default function Schedules() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [tasks, setTasks] = useState<CrawlTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Schedule | null>(null);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try {
      const [s, t] = await Promise.all([fetchSchedules(), fetchTasks()]);
      setSchedules(s);
      setTasks(t);
    } catch (e: unknown) {
      message.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const payload = {
        name: values.name as string,
        task_ids: (values.task_ids as string[]) || [],
        cron_expression: values.cron_expression as string,
        enabled: (values.enabled as boolean) ?? true,
      };

      if (editing) {
        await updateSchedule(editing._id, payload);
        message.success("定时任务已更新");
      } else {
        await createSchedule(payload);
        message.success("定时任务已创建");
      }
      setModalOpen(false);
      setEditing(null);
      form.resetFields();
      load();
    } catch (e: unknown) {
      message.error((e as Error).message);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteSchedule(id);
      message.success("已删除");
      load();
    } catch (e: unknown) {
      message.error((e as Error).message);
    }
  };

  const openEdit = (schedule: Schedule) => {
    setEditing(schedule);
    form.setFieldsValue(schedule);
    setModalOpen(true);
  };

  const columns: ColumnsType<Schedule> = [
    { title: "名称", dataIndex: "name", key: "name" },
    { title: "Cron表达式", dataIndex: "cron_expression", key: "cron_expression" },
    {
      title: "关联任务",
      dataIndex: "task_ids",
      key: "task_ids",
      render: (ids: string[]) =>
        ids.map((id) => {
          const task = tasks.find((t) => t._id === id);
          return <Tag key={id}>{task?.name || id}</Tag>;
        }),
    },
    {
      title: "状态",
      dataIndex: "enabled",
      key: "enabled",
      render: (enabled: boolean) => (
        <Tag color={enabled ? "green" : "red"}>{enabled ? "启用" : "禁用"}</Tag>
      ),
    },
    {
      title: "操作",
      key: "actions",
      render: (_: unknown, record: Schedule) => (
        <Space>
          <Button icon={<EditOutlined />} size="small" onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record._id)}>
            <Button danger icon={<DeleteOutlined />} size="small">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            setEditing(null);
            form.resetFields();
            form.setFieldsValue({ enabled: true, task_ids: [], cron_expression: "0 2 * * *" });
            setModalOpen(true);
          }}
        >
          新建定时任务
        </Button>
      </div>

      <Table columns={columns} dataSource={schedules} rowKey="_id" loading={loading} />

      <Modal
        title={editing ? "编辑定时任务" : "新建定时任务"}
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          setEditing(null);
        }}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="每日凌晨爬取" />
          </Form.Item>
          <Form.Item name="cron_expression" label="Cron表达式" rules={[{ required: true }]}>
            <Input placeholder="0 2 * * *" />
          </Form.Item>
          <Form.Item name="task_ids" label="关联任务">
            <Select
              mode="multiple"
              placeholder="选择要执行的任务"
              options={tasks.map((t) => ({ value: t._id, label: t.name }))}
            />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
```

- [ ] **Step 4: Create Movies page**

Write `frontend/src/pages/Movies.tsx`:
```tsx
import { useEffect, useState, useCallback } from "react";
import {
  Table, Input, Select, Button, Space, Card, message, Drawer, Descriptions, Tag, Typography,
} from "antd";
import { SearchOutlined, ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { fetchCollections, fetchMovies, fetchMovie, MovieListResponse } from "../api/movies";

export default function Movies() {
  const [collections, setCollections] = useState<string[]>([]);
  const [selectedCollection, setSelectedCollection] = useState("movies");
  const [search, setSearch] = useState("");
  const [data, setData] = useState<MovieListResponse>({ items: [], total: 0, page: 1, limit: 20, total_pages: 1 });
  const [loading, setLoading] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);

  const loadCollections = useCallback(async () => {
    try {
      const cols = await fetchCollections();
      setCollections(cols);
      if (cols.length > 0 && !cols.includes(selectedCollection)) {
        setSelectedCollection(cols[0]);
      }
    } catch (e: unknown) {
      message.error((e as Error).message);
    }
  }, []);

  const loadMovies = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const result = await fetchMovies({
        collection: selectedCollection,
        search: search || undefined,
        page,
        limit: 20,
      });
      setData(result);
    } catch (e: unknown) {
      message.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [selectedCollection, search]);

  useEffect(() => {
    loadCollections();
  }, [loadCollections]);

  useEffect(() => {
    loadMovies();
  }, [loadMovies]);

  const handleViewDetail = async (id: string) => {
    try {
      const movie = await fetchMovie(id, selectedCollection);
      setDetail(movie);
      setDetailOpen(true);
    } catch (e: unknown) {
      message.error((e as Error).message);
    }
  };

  const columns: ColumnsType<Record<string, unknown>> = [
    { title: "番号", dataIndex: "code", key: "code", width: 140 },
    {
      title: "标题",
      dataIndex: "title",
      key: "title",
      ellipsis: true,
      render: (text: string) => text || "-",
    },
    { title: "日期", dataIndex: "date", key: "date", width: 110 },
    {
      title: "标签",
      dataIndex: "tags",
      key: "tags",
      width: 250,
      render: (tags: string[]) =>
        Array.isArray(tags) ? (
          <Space size={[0, 4]} wrap>
            {tags.slice(0, 5).map((tag: string) => (
              <Tag key={tag}>{tag}</Tag>
            ))}
            {tags.length > 5 && <Tag>+{tags.length - 5}</Tag>}
          </Space>
        ) : null,
    },
    {
      title: "操作",
      key: "actions",
      width: 80,
      render: (_: unknown, record: Record<string, unknown>) => (
        <Button type="link" size="small" onClick={() => handleViewDetail(record._id as string)}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select
            style={{ width: 200 }}
            value={selectedCollection}
            onChange={setSelectedCollection}
            options={collections.map((c) => ({ value: c, label: c }))}
            placeholder="选择集合"
          />
          <Input
            style={{ width: 300 }}
            placeholder="搜索番号、标题..."
            prefix={<SearchOutlined />}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onPressEnter={() => loadMovies()}
            allowClear
          />
          <Button type="primary" onClick={() => loadMovies()}>
            搜索
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => { setSearch(""); loadMovies(1); }}>
            刷新
          </Button>
        </Space>
      </Card>

      <Table
        columns={columns}
        dataSource={data.items}
        rowKey="_id"
        loading={loading}
        pagination={{
          current: data.page,
          total: data.total,
          pageSize: data.limit,
          onChange: (page) => loadMovies(page),
          showTotal: (total) => `共 ${total} 条`,
        }}
      />

      <Drawer
        title="影片详情"
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        width={600}
      >
        {detail && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="番号">{detail.code as string}</Descriptions.Item>
            <Descriptions.Item label="标题">{detail.title as string}</Descriptions.Item>
            <Descriptions.Item label="日期">{detail.date as string}</Descriptions.Item>
            <Descriptions.Item label="时长">{detail.length as string}</Descriptions.Item>
            <Descriptions.Item label="导演">{detail.director as string}</Descriptions.Item>
            <Descriptions.Item label="制作商">{detail.maker as string}</Descriptions.Item>
            <Descriptions.Item label="发行商">{detail.publisher as string}</Descriptions.Item>
            <Descriptions.Item label="演员">
              {Array.isArray(detail.actors)
                ? (detail.actors as string[]).map((a: string) => <Tag key={a}>{a}</Tag>)
                : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="标签">
              {Array.isArray(detail.tags)
                ? (detail.tags as string[]).map((t: string) => <Tag key={t}>{t}</Tag>)
                : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="封面">
              {detail.cover as string ? (
                <img
                  src={detail.cover as string}
                  alt="cover"
                  style={{ maxWidth: 200 }}
                  referrerPolicy="no-referrer"
                />
              ) : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="来源URL">
              <Typography.Link href={detail.source_url as string} target="_blank">
                {detail.source_url as string}
              </Typography.Link>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
}
```

- [ ] **Step 5: Build and verify**

```bash
cd frontend && npm run build
```
Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/settings.ts frontend/src/api/schedules.ts frontend/src/api/movies.ts frontend/src/pages/Settings.tsx frontend/src/pages/Schedules.tsx frontend/src/pages/Movies.tsx
git commit -m "feat: add settings, schedules, and movies content browsing pages"
```

---

### Task 9: End-to-End Integration + Docker Verification

**Files:**
- Create: `backend/.dockerignore`
- Create: `frontend/.dockerignore`
- Modify: `.gitignore`

**Goal:** Verify all three Docker services start and communicate correctly.

- [ ] **Step 1: Create .dockerignore files**

Write `backend/.dockerignore`:
```
.venv/
__pycache__/
*.pyc
.env
.git/
logs/*.log
.pytest_cache/
```

Write `frontend/.dockerignore`:
```
node_modules/
dist/
.git/
```

- [ ] **Step 2: Append to .gitignore**

Add to `.gitignore`:
```
frontend/node_modules/
frontend/dist/
mongo_data/
```

- [ ] **Step 3: Full Docker build and up**

```bash
docker compose build --no-cache
docker compose up -d
```

- [ ] **Step 4: Verify all services healthy**

```bash
# Check MongoDB
docker compose exec mongo mongosh --eval "db.runCommand('ping').ok"

# Check backend health
curl http://localhost:8000/health

# Check frontend
curl -s http://localhost/ | head -5
```

Expected: All return success responses.

- [ ] **Step 5: Verify API through frontend proxy**

```bash
curl http://localhost/api/health
```
Expected: Same health response as direct backend call.

- [ ] **Step 6: Run full backend test suite**

```bash
docker compose exec backend python -m pytest tests/ -v
```
Expected: All tests pass.

- [ ] **Step 7: Tear down and commit**

```bash
docker compose down
git add backend/.dockerignore frontend/.dockerignore .gitignore
git commit -m "feat: add dockerignore files and final integration verification"
```

---

## Self-Review

**Spec coverage check:**
- [x] Dockerize project → Task 1 (Dockerfile, docker-compose), Task 9 (verification)
- [x] Configure task tasks → Task 3 (Task CRUD API), Task 7 (Task config page)
- [x] Configure database connections → Task 2 (Settings API), Task 8 (Settings page)
- [x] Configure scheduled tasks → Task 5 (Schedule API), Task 8 (Schedules page)
- [x] List + query to view crawler content → Task 4 (Movies query API), Task 8 (Movies page)

**Placeholder scan:** No TBD, TODO, or "implement later" found. All code is concrete.

**Type consistency check:**
- `CrawlTask._id` is `str` in all frontend types ✓
- `FilterConfig` fields match between backend Pydantic and frontend TypeScript ✓
- Schedule `task_ids` is `string[]` everywhere ✓
- API paths match between frontend clients and backend routers ✓
