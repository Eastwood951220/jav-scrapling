import json

from fastapi import APIRouter

from app.models.cookies_config import CookiesConfig
from scraper.config.settings import COOKIE_DIR

router = APIRouter(prefix="/api/settings", tags=["settings"])
DEFAULT_COOKIE_FILE = "javdb_cookies.json"


def _get_cookie_path():
    return COOKIE_DIR / DEFAULT_COOKIE_FILE


@router.get("/cookies", response_model=CookiesConfig)
def get_cookies_config():
    """Read the default cookie file used by the scraper."""
    filepath = _get_cookie_path()
    if not filepath.exists():
        return CookiesConfig(cookies=[])
    try:
        with filepath.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return CookiesConfig(cookies=[])
    if isinstance(data, list):
        return CookiesConfig(cookies=data)
    # Old flat dict format — convert to minimal list for backward compat
    if isinstance(data, dict):
        cookies_list = [
            {"name": k, "value": v, "domain": "javdb.com", "path": "/"}
            for k, v in data.items()
        ]
        return CookiesConfig(cookies=cookies_list)
    return CookiesConfig(cookies=[])


@router.put("/cookies", response_model=CookiesConfig)
def update_cookies_config(body: CookiesConfig):
    """Save cookies to the default cookie file used by the scraper."""
    filepath = _get_cookie_path()
    filepath.parent.mkdir(parents=True, exist_ok=True)
    cookies_list = [cookie.model_dump() for cookie in body.cookies]
    with filepath.open("w", encoding="utf-8") as f:
        json.dump(cookies_list, f, ensure_ascii=False, indent=2)
    return body
