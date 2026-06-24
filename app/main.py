from database.mongo_client import close_mongo, connect_mongo
from tasks.task_manager import TaskManager


def main():
    connect_mongo()

    try:
        manager = TaskManager()
        result = manager.run_from_config()
    finally:
        close_mongo()

    if result:
        print(result)


if __name__ == "__main__":
    main()
