# jav-scrapling

基于 Scrapling 的 JavDB 爬虫项目。

## 安装

```bash
pip install -r requirements.txt
scrapling install
```

## 配置

复制环境变量文件：

```bash
cp .env.example .env
```

配置 MongoDB：

```env
MONGO_URI=mongodb://admin:admin123@localhost:27017/
MONGO_DB_NAME=jav
MONGO_CONNECT_TIMEOUT_MS=5000
```

全局爬取参数：

```env
MAX_LIST_PAGES=50
LIST_PAGE_DELAY_MIN=4
LIST_PAGE_DELAY_MAX=5
DETAIL_PAGE_DELAY_MIN=2
DETAIL_PAGE_DELAY_MAX=3
SECURITY_WAIT_SECONDS=120
```

## Cookie

Cookie 文件放在：

```text
cookies/storage/javdb_cookies.json
```

该文件不会提交 Git。

## 运行

```bash
python -m app.main
```

## 任务配置

编辑：

```text
tasks/task.yml
```

示例：

```yaml
tasks:
  - name: "VR"
    url: "https://javdb.com/actors/ZXy46?t=d&sort_type=0"
    url_type: "actors"
    is_skip: false
    filter:
      only_chinese: false
      exclude_multi_person: false
```

## 测试

```bash
pytest
```

## 数据库结构

所有电影数据统一存储在 `movies` 集合中，每条记录包含 `source_task_name` 字段标识数据来源。

### 集合列表

| 集合 | 说明 |
|------|------|
| `movies` | 统一电影集合 |
| `config_tasks` | 任务配置 |
| `config_schedules` | 调度配置 |
| `config_settings` | 全局设置 |
| `task_runs` | 任务运行记录 |
| `run_detail_tasks` | 运行详情 |

### 数据迁移

如果从旧版本升级，需要将分散在各任务集合中的电影数据迁移到统一集合：

```bash
# 试运行查看迁移计划
python scripts/migrate_movie_collections.py --dry-run

# 执行迁移
python scripts/migrate_movie_collections.py
```

### 清理旧集合

迁移完成后，可清理旧的电影集合：

```bash
# 试运行查看清理计划
python scripts/cleanup_old_collections.py --dry-run

# 执行清理（需要确认）
python scripts/cleanup_old_collections.py
```

## 目录说明

- `app/`：程序入口
- `config/`：配置
- `core/`：通用基础能力
- `cookies/`：Cookie 读取和保存
- `fetchers/`：Scrapling 请求封装
- `spiders/`：爬虫流程和页面解析
- `pipelines/`：数据清洗和入库前处理
- `database/`：数据库连接和仓储
- `services/`：业务编排
- `tasks/`：任务调度
- `scripts/`：独立辅助脚本
