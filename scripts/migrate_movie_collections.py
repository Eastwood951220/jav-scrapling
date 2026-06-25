#!/usr/bin/env python3
"""电影数据迁移脚本。

将分散在多个集合中的电影数据迁移到统一的 movies 集合。

使用方法:
    python scripts/migrate_movie_collections.py [--dry-run]

选项:
    --dry-run   仅显示迁移计划，不执行实际迁移
"""

import argparse
import sys
from datetime import datetime

from pymongo import MongoClient

from scraper.config.settings import MONGO_URI, MONGO_DB_NAME
from scraper.database.indexes import ensure_indexes


# 系统集合（非电影数据）
SYSTEM_COLLECTIONS = {
    "config_tasks",
    "config_schedules",
    "config_settings",
    "task_runs",
    "run_detail_tasks",
    "movies",  # 目标集合，跳过
}


def get_movie_collections(db) -> list[str]:
    """获取所有包含电影数据的集合。"""
    all_collections = db.list_collection_names()
    return [name for name in all_collections if name not in SYSTEM_COLLECTIONS]


def migrate_collection(db, source_name: str, dry_run: bool = False) -> dict:
    """迁移单个集合的数据。

    Args:
        db: 数据库实例
        source_name: 源集合名称
        dry_run: 是否为试运行

    Returns:
        迁移统计信息
    """
    source_col = db[source_name]
    target_col = db["movies"]

    stats = {"total": 0, "migrated": 0, "skipped": 0, "errors": 0}

    # 获取源集合中的所有文档
    cursor = source_col.find({})
    for doc in cursor:
        stats["total"] += 1

        # 添加来源标识
        doc["source_task_name"] = source_name
        doc.setdefault("updated_at", datetime.now())

        # 确定唯一字段
        code = doc.get("code")
        unique_field = "code" if code else "source_url"

        if not doc.get(unique_field):
            stats["errors"] += 1
            print(f"  [ERROR] 文档缺少唯一字段 {unique_field}: {doc.get('_id')}")
            continue

        # 检查目标集合中是否已存在
        existing = target_col.find_one({unique_field: doc[unique_field]})
        if existing:
            stats["skipped"] += 1
            continue

        if not dry_run:
            try:
                # 移除旧的 _id，让 MongoDB 生成新的
                doc.pop("_id", None)
                target_col.insert_one(doc)
                stats["migrated"] += 1
            except Exception as e:
                stats["errors"] += 1
                print(f"  [ERROR] 迁移失败: {e}")
        else:
            stats["migrated"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="迁移电影数据到统一集合")
    parser.add_argument("--dry-run", action="store_true", help="仅显示迁移计划")
    args = parser.parse_args()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}开始电影数据迁移...")
    print(f"数据库: {MONGO_DB_NAME}")
    print()

    # 连接数据库
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]

    # 确保目标集合索引存在
    if not args.dry_run:
        ensure_indexes(db, "movies")
        print("已创建目标集合索引")
        print()

    # 获取需要迁移的集合
    collections = get_movie_collections(db)
    if not collections:
        print("没有找到需要迁移的电影集合")
        return

    print(f"找到 {len(collections)} 个电影集合需要迁移:")
    for name in collections:
        count = db[name].count_documents({})
        print(f"  - {name}: {count} 条记录")
    print()

    # 执行迁移
    total_stats = {"total": 0, "migrated": 0, "skipped": 0, "errors": 0}

    for collection_name in collections:
        print(f"迁移集合: {collection_name}")
        stats = migrate_collection(db, collection_name, args.dry_run)

        print(f"  总计: {stats['total']}, "
              f"迁移: {stats['migrated']}, "
              f"跳过: {stats['skipped']}, "
              f"错误: {stats['errors']}")

        # 累加统计
        for key in total_stats:
            total_stats[key] += stats[key]

    print()
    print("迁移完成!")
    print(f"总计: {total_stats['total']}, "
          f"迁移: {total_stats['migrated']}, "
          f"跳过: {total_stats['skipped']}, "
          f"错误: {total_stats['errors']}")

    if args.dry_run:
        print()
        print("这是试运行，未执行实际迁移。去掉 --dry-run 参数执行实际迁移。")


if __name__ == "__main__":
    main()
