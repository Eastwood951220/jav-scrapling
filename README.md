# jav-scrapling

基于 FastAPI、React、MongoDB 和 Scrapling 的 JavDB 爬取与管理工具。项目提供任务配置、定时任务、运行历史、日志/结果查看、电影内容浏览和系统设置页面。

## 功能概览

- 爬取 JavDB 列表页和详情页，保存影片详情、磁力信息、标签、演员、评分等字段。
- 通过 Web UI 管理任务配置、定时任务、运行历史和系统设置。
- 后端使用 MongoDB 保存配置、运行摘要和影片数据。
- 运行日志写入 `run_data/runs/` 和 `run_data/storage_tasks/`，运行结果摘要保存在 MongoDB。
- 支持 Docker Compose 部署，也支持本地前后端分离开发。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 后端 | FastAPI、Uvicorn、Pydantic、APScheduler |
| 爬虫 | Scrapling、JavDB spider、Cookie 管理 |
| 数据库 | MongoDB、PyMongo |
| 前端 | React 19、Vite、TypeScript、Ant Design、TanStack Router |
| 部署 | Docker Compose、Nginx |

## 项目结构

```text
.
├── backend/                  # FastAPI 后端、模块化 API、任务队列、调度器
│   ├── app/
│   │   ├── core/             # BSON、日志、依赖注入等基础设施
│   │   ├── db/               # 兼容层，re-export shared.database
│   │   ├── modules/          # crawler/storage/content 大模块
│   │   ├── main.py           # FastAPI 入口
│   │   ├── scheduler.py      # APScheduler 定时任务
│   └── requirements.txt
├── frontend/                 # React 管理界面源码
├── scraper/                  # 爬虫、解析、清洗
│   ├── config/               # 环境变量、站点配置
│   ├── database/             # 兼容层，delegate to shared.database
│   ├── fetchers/
│   ├── pipelines/
│   ├── services/
│   ├── spiders/
│   └── tasks/
├── shared/                   # 共享基础设施（backend 和 scraper 共用）
│   ├── database/             # MongoDB 客户端、集合常量、索引、仓储
│   └── integrations/         # CloudDrive2 gRPC、JavDB 边界导入
├── scripts/                  # 电影集合迁移/清理脚本
├── docker-compose.yml
├── Makefile
└── .env.example
```

### 依赖方向

```text
backend ─┐
         ├── shared
scraper ─┘
```

Backend 和 scraper 都依赖 shared，但彼此不直接依赖数据库或集成层。

## 快速开始

### 1. 准备环境变量

```bash
cp .env.example .env
```

常用配置：

```env
MONGO_URI=mongodb://admin:admin123@localhost:27017/
MONGO_DB_NAME=jav
MONGO_CONNECT_TIMEOUT_MS=5000

REQUEST_TIMEOUT=30
USE_DYNAMIC_FETCHER=false

MAX_LIST_PAGES=50
LIST_PAGE_DELAY_MIN=4
LIST_PAGE_DELAY_MAX=5
DETAIL_PAGE_DELAY_MIN=2
DETAIL_PAGE_DELAY_MAX=3
SECURITY_WAIT_SECONDS=120
```

使用 Docker Compose 时，后端容器会通过 `mongo:27017` 连接 MongoDB；宿主机访问 compose 中的 MongoDB 端口是 `localhost:27018`。如果本地后端要连接 compose 启动的 MongoDB，请把 `.env` 中的 `MONGO_URI` 改为 `mongodb://admin:admin123@localhost:27018/?authSource=admin`。

### 2. Cookie 文件

本地运行时 Cookie 默认放在：

```text
scraper/cookies/storage/javdb_cookies.json
```

Docker 运行时该目录映射到：

```text
docker/cookies/
```

Cookie 文件不应提交到 Git。

## Docker 运行

项目提供 Makefile 封装常用 Docker 命令：

```bash
make start
make logs
make status
make stop
```

服务地址：

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:18643 |
| 后端 | http://localhost:18642 |
| API 文档 | http://localhost:18642/docs |
| 健康检查 | http://localhost:18642/health |
| MongoDB | localhost:27018 |

注意：当前 `docker-compose.yml` 的前端构建上下文指向 `./docker/frontend`，该目录目前只有 `nginx.conf`。如果 `docker compose up --build` 在前端构建阶段失败，需要补齐 `docker/frontend/Dockerfile`，或把 compose 的前端构建配置调整为 `frontend/Dockerfile`。

## 本地开发

### 后端

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
scrapling install
```

启动后端：

```bash
cd backend
PYTHONPATH=".:..:$PYTHONPATH" ../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 18642 --reload
```

也可以使用 Makefile：

```bash
make dev-backend
```

### 前端

```bash
cd frontend
npm ci
npm run dev
```

前端开发服务器默认运行在：

```text
http://localhost:18643
```

Vite 会把 `/api` 请求代理到：

```text
http://localhost:18642
```

也可以使用 Makefile 同时启动前后端：

```bash
make dev
```

## API 模块

| 路由前缀 | 说明 |
| --- | --- |
| `/api/tasks` | 创建、更新、删除任务配置，触发任务运行 |
| `/api/runs` | 查看运行历史、运行详情、队列状态、停止任务 |
| `/api/schedules` | 创建、更新、删除定时任务 |
| `/api/movies` | 浏览统一电影集合，支持搜索、分页、排序、评分过滤 |
| `/api/config` | 查看和更新当前进程环境配置 |
| `/api/config/cookies` | Cookie 配置相关接口 |

## Fresh Data Reset

This version uses fresh MongoDB collection names for crawl task history:
`crawl_tasks`, `crawl_runs`, and `crawl_run_detail_tasks`. Existing
`config_tasks`, `task_runs`, and `run_detail_tasks` data is not read.

Execution logs are stored as JSONL files:

- Crawl runs: `run_data/runs/{run_id}.jsonl`
- Storage tasks: `run_data/storage_tasks/{task_id}.jsonl`

To start clean in local Docker, stop the stack and remove the MongoDB and
runtime-data volumes/directories configured in `docker-compose.yml`, then start
the stack again with `make start`.

## 数据存储

### MongoDB 集合

| 集合 | 说明 |
| --- | --- |
| `movies` | 统一电影集合，当前电影仓储写入该集合 |
| `crawl_tasks` | 任务配置 |
| `crawl_schedules` | 定时任务配置 |
| `crawl_config` | 系统配置预留集合 |
| `crawl_runs` | 任务运行记录和结果摘要 |
| `crawl_run_detail_tasks` | 详情任务状态，供失败重试等功能使用 |
| `storage_config` | 存储配置 |
| `storage_tasks` | 存储任务 |
| `storage_counters` | 存储任务 ID 计数器 |

### 文件存储

运行日志保存在：

```text
run_data/runs/{run_id}.jsonl
run_data/storage_tasks/{task_id}.jsonl
```

Docker 运行时对应宿主机目录：

```text
docker/run_data/
```

## 电影集合与索引

当前电影仓储使用统一集合：

```text
movies
```

电影数据通过 `code` 或 `source_url` 去重。索引定义在：

```text
shared/database/indexes/
```

主要索引包括：

- `code` 唯一稀疏索引
- `source_url` 唯一稀疏索引
- `source_task_name + code` 组合索引
- `release_date` 倒序索引
- `rating` 倒序稀疏索引
- `created_at`、`updated_at` 倒序索引
- `title + code` 组合索引

索引会在电影仓储首次写入时懒初始化。迁移脚本也会在写入 `movies` 前确保索引存在。

## 旧电影集合迁移

如果数据库中仍存在按任务名分散的旧电影集合，可以迁移到统一 `movies` 集合。

试运行：

```bash
python scripts/migrate_movie_collections.py --dry-run
```

执行迁移：

```bash
python scripts/migrate_movie_collections.py
```

迁移完成并确认数据无误后，可以清理旧集合。

试运行：

```bash
python scripts/cleanup_old_collections.py --dry-run
```

执行清理：

```bash
python scripts/cleanup_old_collections.py
```

## 常用命令

```bash
# Docker
make start
make stop
make restart
make logs
make status
make build

# 本地开发
make dev-backend
make dev-frontend
make dev

# 后端测试
cd backend
PYTHONPATH=".:..:$PYTHONPATH" pytest

# 前端构建
cd frontend
npm run build
```

## 当前实现注意事项

- 任务队列是单进程内存队列，后端重启后不会自动恢复内存中的排队任务。
- `/api/config` 更新的是当前进程环境变量，已在模块导入时读取的配置常量需要重启后才会完全生效。
- 运行日志目前按 JSON 文件整体读写，日志量很大时建议后续改为 JSONL 追加写。
- `backend/app/api/tasks.py` 中创建任务时仍保留旧的“创建任务同名集合”逻辑；电影仓储和电影 API 已使用统一 `movies` 集合。
- 不建议提交 `docker/mongo_data/`、`docker/run_data/`、`docker/cookies/`、`run_data/` 等运行数据目录。
