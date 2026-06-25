import os

from fastapi import APIRouter, HTTPException

from app.models.setting import SettingItem, SettingUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])

SETTING_KEYS = [
    "MAX_LIST_PAGES", "LIST_PAGE_DELAY_MIN", "LIST_PAGE_DELAY_MAX",
    "DETAIL_PAGE_DELAY_MIN", "DETAIL_PAGE_DELAY_MAX", "SECURITY_WAIT_SECONDS",
    "REQUEST_TIMEOUT", "USE_DYNAMIC_FETCHER",
    "MONGO_URI", "MONGO_DB_NAME", "MONGO_CONNECT_TIMEOUT_MS",
    "BATCH_SAVE_SIZE",
]


def _read_settings() -> dict:
    from scraper.config import settings as cfg

    # Default values sourced from scraper.config.settings module
    _DEFAULTS = {
        "MAX_LIST_PAGES": cfg.MAX_LIST_PAGES,
        "LIST_PAGE_DELAY_MIN": cfg.LIST_PAGE_DELAY_MIN,
        "LIST_PAGE_DELAY_MAX": cfg.LIST_PAGE_DELAY_MAX,
        "DETAIL_PAGE_DELAY_MIN": cfg.DETAIL_PAGE_DELAY_MIN,
        "DETAIL_PAGE_DELAY_MAX": cfg.DETAIL_PAGE_DELAY_MAX,
        "SECURITY_WAIT_SECONDS": cfg.SECURITY_WAIT_SECONDS,
        "REQUEST_TIMEOUT": cfg.REQUEST_TIMEOUT,
        "USE_DYNAMIC_FETCHER": cfg.USE_DYNAMIC_FETCHER,
        "MONGO_URI": cfg.MONGO_URI,
        "MONGO_DB_NAME": cfg.MONGO_DB_NAME,
        "MONGO_CONNECT_TIMEOUT_MS": cfg.MONGO_CONNECT_TIMEOUT_MS,
        "BATCH_SAVE_SIZE": int(os.getenv("BATCH_SAVE_SIZE", "50")),
    }

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
        elif key in _DEFAULTS:
            result[key] = _DEFAULTS[key]
    return result


@router.get("")
def get_settings():
    return _read_settings()


@router.put("")
def update_settings(body: SettingUpdate):
    # NOTE: This updates os.environ for the current process.
    # Module-level constants in config/settings.py are loaded at import time
    # and won't reflect changes until the process restarts.
    # A restart is needed for changes to take full effect.
    updated = body.model_dump(exclude_none=True)
    for key, value in updated.items():
        os.environ[key] = str(value)
    return _read_settings()
