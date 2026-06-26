import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.db.collections import STORAGE_CONFIG
from app.modules.storage.config.schemas import (
    StorageConfig,
    StorageConfigResponse,
    StorageTestResult,
)
from scraper.database.mongo_client import get_mongo_db

router = APIRouter(prefix="/api/storage/config", tags=["storage-config"])

STORAGE_CONFIG_COLLECTION = STORAGE_CONFIG

logger = logging.getLogger("storage_config")

# Default config document key
_CONFIG_KEY = {"_key": "default"}


def _mask_token(token: str) -> str:
    """Mask API token for safe display. Show only last 4 chars."""
    if not token or len(token) < 8:
        return "****" if token else ""
    return f"{'*' * 12}{token[-4:]}"


def _is_masked(token: str) -> bool:
    """Check if a token value is already masked."""
    if not token:
        return False
    # Masked pattern: all asterisks optionally followed by 4 chars
    stripped = token.rstrip("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return stripped and all(c == "*" for c in stripped) and len(stripped) >= 4


@router.get("/", response_model=StorageConfigResponse)
def get_storage_config():
    """Read storage config from MongoDB. Token is always masked in response."""
    db = get_mongo_db()
    doc = db[STORAGE_CONFIG_COLLECTION].find_one(_CONFIG_KEY)

    if not doc:
        return StorageConfigResponse()

    doc.pop("_id", None)
    doc.pop("_key", None)

    # Mask the token for display
    raw_token = doc.get("api_token", "")
    doc["api_token"] = _mask_token(raw_token) if raw_token else ""

    return StorageConfigResponse(**doc)


@router.put("", response_model=StorageConfigResponse)
def update_storage_config(body: StorageConfig):
    """Save storage config to MongoDB."""
    db = get_mongo_db()

    update_data = body.model_dump()

    # If token is empty or masked, preserve existing token
    incoming_token = update_data.get("api_token", "")
    if not incoming_token or _is_masked(incoming_token):
        existing = db[STORAGE_CONFIG_COLLECTION].find_one(_CONFIG_KEY)
        if existing:
            update_data["api_token"] = existing.get("api_token", "")
        else:
            update_data["api_token"] = ""

    # Validate delay ranges
    if update_data["operation_delay_max"] < update_data["operation_delay_min"]:
        raise HTTPException(
            status_code=400,
            detail="operation_delay_max must be >= operation_delay_min",
        )
    if update_data["download_poll_interval_max"] < update_data["download_poll_interval_min"]:
        raise HTTPException(
            status_code=400,
            detail="download_poll_interval_max must be >= download_poll_interval_min",
        )
    if update_data["retry_delay_max"] < update_data["retry_delay_min"]:
        raise HTTPException(
            status_code=400,
            detail="retry_delay_max must be >= retry_delay_min",
        )

    update_data["updated_at"] = datetime.now()

    db[STORAGE_CONFIG_COLLECTION].update_one(
        _CONFIG_KEY,
        {"$set": update_data},
        upsert=True,
    )

    # Return with masked token
    response_data = {**update_data,
                     "api_token": _mask_token(update_data["api_token"]) if update_data["api_token"] else ""}

    return StorageConfigResponse(**response_data)


@router.post("/test", response_model=StorageTestResult)
def test_storage_connection():
    """Test CloudDrive2 connection. Stub implementation for now."""
    # TODO: Implement real CloudDrive2 gRPC health check
    return StorageTestResult(
        grpc_reachable=False,
        grpc_error="CloudDrive2 connection test not yet implemented",
        api_authorized=False,
        api_error=None,
        download_root_exists=False,
        download_root_error=None,
        target_folder_accessible=False,
        target_folder_error=None,
    )
