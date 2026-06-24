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
