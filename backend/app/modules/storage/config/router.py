import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.db.collections import STORAGE_CONFIG
from scraper.services.clouddrive_grpc_client import CloudDriveGrpcClient
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


@router.get("", response_model=StorageConfigResponse)
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


def _extract_auth_error(exc: Exception) -> str:
    """Extract a user-friendly auth error message from a gRPC error."""
    import grpc

    if isinstance(exc, grpc.RpcError):
        code = exc.code()
        if code == grpc.StatusCode.UNAUTHENTICATED:
            return "Token 无效或已过期 (UNAUTHENTICATED)"
        if code == grpc.StatusCode.PERMISSION_DENIED:
            return "Token 权限不足 (PERMISSION_DENIED)"
        return f"gRPC 错误: {code.name}: {exc.details()[:150]}"
    return str(exc)[:200]


def _check_folder(
    cd2: CloudDriveGrpcClient,
    folder_path: str,
    result: StorageTestResult,
    check_type: str,
) -> None:
    """Check if a folder exists and update the result accordingly.

    Args:
        cd2: Authenticated gRPC client.
        folder_path: Absolute path to check (e.g. '/Downloads').
        result: StorageTestResult to update.
        check_type: Either 'download_root' or 'target'.
    """
    import posixpath

    parent = posixpath.dirname(folder_path) or "/"
    name = posixpath.basename(folder_path)

    try:
        found = cd2.find_file_by_path(parent, name)
        if found is not None:
            if check_type == "download_root":
                result.download_root_exists = True
            else:
                result.target_folder_accessible = True
        else:
            if check_type == "download_root":
                result.download_root_exists = False
                result.download_root_error = f"路径不存在: {folder_path}"
            else:
                result.target_folder_accessible = False
                result.target_folder_error = f"路径不存在: {folder_path}"
    except Exception as exc:
        if check_type == "download_root":
            result.download_root_exists = False
            result.download_root_error = str(exc)[:200]
        else:
            result.target_folder_accessible = False
            result.target_folder_error = str(exc)[:200]


@router.post("/test", response_model=StorageTestResult)
def test_storage_connection():
    """Test CloudDrive2 connection: reachability, token, and folder access."""
    db = get_mongo_db()
    doc = db[STORAGE_CONFIG_COLLECTION].find_one(_CONFIG_KEY)

    raw_host = (doc or {}).get("grpc_host", "localhost:9798")
    token = (doc or {}).get("api_token", "")
    timeout = (doc or {}).get("connect_timeout_seconds", 10)
    download_root = (doc or {}).get("download_root_folder", "/Downloads")
    target_folder = (doc or {}).get("target_folder", "/Movies")

    # Strip protocol prefix — gRPC uses host:port only
    host = raw_host
    if host.startswith("http://"):
        host = host[7:]
    elif host.startswith("https://"):
        host = host[8:]
    host = host.rstrip("/")

    result = StorageTestResult()

    with CloudDriveGrpcClient(host=host, token=token, timeout=timeout) as cd2:
        # --- 1. gRPC reachable (GetSystemInfo — no auth needed) ---
        try:
            sys_info = cd2.get_system_info()
            result.grpc_reachable = True
        except Exception as exc:
            result.grpc_reachable = False
            result.grpc_error = str(exc)[:200]
            return result

        # --- 2. Token authorized (list root — needs auth) ---
        if not token:
            result.api_authorized = False
            result.api_error = "未配置 API Token"
            return result

        try:
            cd2.list_sub_files("/")
            result.api_authorized = True
        except Exception as exc:
            result.api_authorized = False
            result.api_error = _extract_auth_error(exc)
            return result

        # --- 3. Download root exists ---
        _check_folder(cd2, download_root, result, "download_root")

        # --- 4. Target folder accessible ---
        _check_folder(cd2, target_folder, result, "target")

    return result
