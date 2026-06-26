# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JavDB scraping and management tool built with FastAPI, React, MongoDB, and Scrapling. Crawls movie listings and details from JavDB, stores them in MongoDB, and provides a web UI for task management, scheduling, and content browsing.

## Tech Stack

- **Backend**: FastAPI, Uvicorn, Pydantic, APScheduler, Scrapling
- **Frontend**: React 19, Vite, TypeScript, Ant Design, TanStack Router
- **Database**: MongoDB 7, PyMongo
- **Deployment**: Docker Compose, Nginx

## Development Commands

### Backend

```bash
# Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
scrapling install

# Run backend (port 18642)
make dev-backend
# Or manually:
cd backend && PYTHONPATH=".:..:$PYTHONPATH" ../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 18642 --reload

# Run tests
cd backend && PYTHONPATH=".:..:$PYTHONPATH" pytest
```

### Frontend

```bash
cd frontend
npm ci
npm run dev    # Port 18643
npm run build  # TypeScript check + Vite build
```

### Docker

```bash
make start    # Start all services
make stop     # Stop all services
make restart  # Restart all services
make logs     # Follow logs
make status   # Show container status
make build    # Rebuild images (no cache)
make dev      # Run both backend and frontend locally
```

## Architecture

### Backend (`backend/app/`)

Modular FastAPI application with three main modules:

- **`modules/crawler/`** - Task management, run queue, schedules, settings, cookies
  - `runs/queue.py` - Single-process in-memory task queue with worker thread
  - `runs/logs.py` - JSONL log file management for run execution
  - `scheduler.py` - APScheduler integration for cron-based scheduling
- **`modules/content/`** - Movie browsing API
- **`modules/storage/`** - CloudDrive2 storage integration, task worker

Core infrastructure:
- `core/bson.py` - BSON serialization helpers
- `core/logging.py` - Application logging configuration
- `db/collections.py` - MongoDB collection name constants
- `db/indexes.py` - Backend-specific index definitions

### Scraper (`scraper/`)

Standalone scraping package (importable by both backend and CLI):

- **`config/`** - Settings from `.env`, site configuration, logging
- **`database/`** - MongoDB client, movie repository, index definitions
- **`fetchers/`** - Scrapling-based HTTP fetchers (static/dynamic)
- **`parsers/`** - JavDB HTML parsers
- **`pipelines/`** - Data cleaning and transformation pipelines
- **`services/`** - Movie service orchestrating crawl workflow
- **`spiders/javdb/`** - JavDB spider, URL builders, schema definitions
- **`tasks/`** - Task schema and utilities

### Frontend (`frontend/src/`)

Feature-based React application using TanStack Router:

- **`features/crawler/`** - Tasks, schedules, runs, settings UI
- **`features/content/`** - Movie browsing
- **`features/storage/`** - CloudDrive2 storage config and tasks
- **`shared/`** - Components, styles, API utilities

## Key Data Flow

1. User creates crawl task via `/api/tasks`
2. Task enqueued to in-memory queue (`queue.py`)
3. Worker thread executes: fetch list pages → parse detail URLs → fetch/parse details → clean data → upsert to `movies` collection
4. Run status and logs tracked in `crawl_runs` collection and `run_data/runs/{run_id}.jsonl`
5. APScheduler can auto-trigger tasks via cron expressions

## MongoDB Collections

| Collection | Purpose |
|------------|---------|
| `movies` | Unified movie data (deduplicated by `code` or `source_url`) |
| `crawl_tasks` | Task configurations |
| `crawl_runs` | Run history and results |
| `crawl_run_detail_tasks` | Per-movie crawl status for retry |
| `crawl_schedules` | Cron schedule configurations |
| `crawl_settings` | System settings |
| `storage_config` | CloudDrive2 storage configurations |
| `storage_tasks` | Storage transfer tasks |

## Environment Variables

Key settings in `.env`:

```env
MONGO_URI=mongodb://admin:admin123@localhost:27017/
MONGO_DB_NAME=jav

# Crawl throttling
MAX_LIST_PAGES=50
LIST_PAGE_DELAY_MIN=4
LIST_PAGE_DELAY_MAX=5
DETAIL_PAGE_DELAY_MIN=2
DETAIL_PAGE_DELAY_MAX=3
SECURITY_WAIT_SECONDS=120
REQUEST_TIMEOUT=30
USE_DYNAMIC_FETCHER=false
```

## Important Notes

- **PYTHONPATH**: Must include both `backend/` and project root when running backend locally
- **Cookie file**: `scraper/cookies/storage/javdb_cookies.json` (local) or `docker/cookies/` (Docker)
- **Task queue**: Single-process in-memory; queued tasks lost on backend restart
- **Run logs**: JSONL format in `run_data/runs/` and `run_data/storage_tasks/`
- **Movie dedup**: Uses `code` (unique sparse) and `source_url` (unique sparse) indexes
- **Vite proxy**: Frontend proxies `/api` to backend (check `vite.config.ts` for current port)

## Running Tests

```bash
# Backend tests
cd backend && PYTHONPATH=".:..:$PYTHONPATH" pytest

# Specific test file
cd backend && PYTHONPATH=".:..:$PYTHONPATH" pytest tests/test_core_bson.py

# With verbose output
cd backend && PYTHONPATH=".:..:$PYTHONPATH" pytest -v
```

## Common Patterns

- Backend modules follow `router.py` (endpoints) + `schemas.py` (Pydantic models) structure
- MongoDB operations use `get_mongo_db()` from `scraper.database.mongo_client`
- All ObjectId conversions go through `app.core.bson.stringify_objectids()`
- Scraping tasks use callback pattern for progress tracking and data flow
