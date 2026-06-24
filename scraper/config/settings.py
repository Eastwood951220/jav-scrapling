import os
from pathlib import Path

from dotenv import load_dotenv

# BASE_DIR now points to project root (one level up from scraper/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://changeme:changeme@localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "jav")
MONGO_CONNECT_TIMEOUT_MS = int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "5000"))

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
USE_DYNAMIC_FETCHER = os.getenv("USE_DYNAMIC_FETCHER", "false").lower() == "true"

MAX_LIST_PAGES = min(int(os.getenv("MAX_LIST_PAGES", "50")), 50)
LIST_PAGE_DELAY_MIN = float(os.getenv("LIST_PAGE_DELAY_MIN", "4"))
LIST_PAGE_DELAY_MAX = float(os.getenv("LIST_PAGE_DELAY_MAX", "5"))
DETAIL_PAGE_DELAY_MIN = float(os.getenv("DETAIL_PAGE_DELAY_MIN", "2"))
DETAIL_PAGE_DELAY_MAX = float(os.getenv("DETAIL_PAGE_DELAY_MAX", "3"))
SECURITY_WAIT_SECONDS = float(os.getenv("SECURITY_WAIT_SECONDS", "120"))

BATCH_SAVE_SIZE = int(os.getenv("BATCH_SAVE_SIZE", "50"))

LOG_DIR = BASE_DIR / "logs"
COOKIE_DIR = BASE_DIR / "scraper" / "cookies" / "storage"
