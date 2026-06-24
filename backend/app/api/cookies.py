import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.models.cookie import CookieFileInfo, CookieContent, CookieUpdate
from scraper.config.settings import COOKIE_DIR
from scraper.cookies.cookie_manager import CookieManager

router = APIRouter(prefix="/api/cookies", tags=["cookies"])


def _normalize_cookies(cookies: dict[str, str] | list[dict[str, str]]) -> dict[str, str]:
    """Normalize cookie input into a flat {name: value} dict."""
    if isinstance(cookies, list):
        return {
            item["name"]: item["value"]
            for item in cookies
            if isinstance(item, dict)
            and "name" in item
            and "value" in item
        }
    return cookies


def _file_info(filepath: Path) -> CookieFileInfo:
    """Build CookieFileInfo from a filesystem path."""
    stat = filepath.stat()
    return CookieFileInfo(
        filename=filepath.name,
        size_bytes=stat.st_size,
        created_at=datetime.fromtimestamp(stat.st_ctime),
    )


@router.get("", response_model=list[CookieFileInfo])
def list_cookie_files():
    """List all cookie files in the storage directory."""
    if not COOKIE_DIR.exists():
        return []
    files = sorted(COOKIE_DIR.glob("*.json"))
    return [_file_info(f) for f in files]


@router.get("/{filename}", response_model=CookieContent)
def get_cookie_file(filename: str):
    """Get the content of a specific cookie file."""
    filepath = COOKIE_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Cookie 文件不存在: {filename}")
    manager = CookieManager(filename)
    cookies = manager.load()
    return CookieContent(filename=filename, cookies=cookies)


@router.put("/{filename}", response_model=CookieContent)
def save_cookie_file(filename: str, body: CookieUpdate):
    """Create or update a cookie file. The request body cookies are saved as-is
    (after normalizing list format to dict) to a JSON file."""
    cookies = _normalize_cookies(body.cookies)
    manager = CookieManager(filename)
    manager.save(cookies)
    return CookieContent(filename=filename, cookies=cookies)


@router.delete("/{filename}")
def delete_cookie_file(filename: str):
    """Delete a cookie file from the storage directory."""
    filepath = COOKIE_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Cookie 文件不存在: {filename}")
    os.remove(filepath)
    return {"detail": f"Cookie 文件已删除: {filename}"}
