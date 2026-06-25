#!/usr/bin/env python3
"""清理旧的电影集合脚本。

警告：此脚本会删除数据，请确保已完成迁移后再执行。

使用方法:
    python scripts/cleanup_old_collections.py [--dry-run]
"""

import argparse

from pymongo import MongoClient

from scraper.config.settings import MONGO_URI, MONGO_DB_NAME

# 系统集合
SYSTEM_COLLECTIONS = {
    "config_tasks",
    "config_schedules",
    "config_settings",
    "task_runs",
    "run_detail_tasks",
    "movies",
}


def main():
    parser = argparse.ArgumentParser(description="清理旧的电影集合")
    parser.add_argument("--dry-run", action="store_true", help="仅显示清理计划")
    args = parser.parse_args()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}开始清理旧集合...")
    print(f"数据库: {MONGO_DB_NAME}")
    print()

    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]

    # 获取非系统集合
    all_collections = db.list_collection_names()
    old_collections = [name for name in all_collections if name not in SYSTEM_COLLECTIONS]

    if not old_collections:
        print("没有找到需要清理的旧集合")
        return

    print(f"找到 {len(old_collections)} 个旧集合:")
    for name in old_collections:
        count = db[name].count_documents({})
        print(f"  - {name}: {count} 条记录")
    print()

    if not args.dry_run:
        confirm = input("确认删除这些集合？(yes/no): ")
        if confirm.lower() != "yes":
            print("取消清理")
            return

    for name in old_collections:
        if args.dry_run:
            print(f"[DRY RUN] 将删除集合: {name}")
        else:
            db.drop_collection(name)
            print(f"已删除集合: {name}")

    print()
    print("清理完成!")


if __name__ == "__main__":
    main()
