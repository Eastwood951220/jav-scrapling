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
