"""CloudDrive2 HTTP API client.

Wraps CloudDrive2's HTTP endpoints for file management and offline downloads.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30
_DEFAULT_DELAY_RANGE = (0.1, 0.5)


class CloudDrive2Client:
    """HTTP client for CloudDrive2 API."""

    def __init__(
        self,
        host: str,
        token: str,
        timeout: int = _DEFAULT_TIMEOUT,
        delay_range: tuple[float, float] = _DEFAULT_DELAY_RANGE,
    ) -> None:
        self.host = host.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.delay_range = delay_range
        self._client: httpx.Client | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _base_url(self) -> str:
        return f"{self.host}/api"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=self.timeout,
                headers=self._headers(),
            )
        return self._client

    def _random_delay(self) -> None:
        lo, hi = self.delay_range
        delay = random.uniform(lo, hi)
        time.sleep(delay)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        logger.debug("GET %s params=%s", url, params)
        resp = self._get_client().get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict[str, Any] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        logger.debug("POST %s data=%s", url, data)
        resp = self._get_client().post(url, json=data)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_connection(self) -> dict[str, Any]:
        """Test connection and token validity."""
        try:
            result = self._get("/list")
            return {
                "connected": True,
                "token_valid": True,
                "message": "ok",
            }
        except httpx.ConnectError as exc:
            logger.warning("CloudDrive2 connection failed: %s", exc)
            return {
                "connected": False,
                "token_valid": False,
                "message": f"connection failed: {exc}",
            }
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                return {
                    "connected": True,
                    "token_valid": False,
                    "message": "invalid token",
                }
            return {
                "connected": True,
                "token_valid": False,
                "message": f"HTTP {exc.response.status_code}",
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("CloudDrive2 check failed: %s", exc)
            return {
                "connected": False,
                "token_valid": False,
                "message": str(exc),
            }

    def list_files(self, path: str) -> list[dict[str, Any]]:
        """List files in a directory."""
        self._random_delay()
        result = self._get("/list", params={"path": path})
        if not isinstance(result, list):
            return []
        return [
            {
                "name": item.get("name", ""),
                "path": item.get("path", path),
                "size": item.get("size", 0),
                "is_dir": item.get("isDir", False),
                "modified": item.get("modified", ""),
            }
            for item in result
        ]

    def create_folder(self, path: str) -> bool:
        """Create a directory. Returns True if created or already exists."""
        self._random_delay()
        try:
            self._post("/createFolder", data={"path": path})
            logger.info("Created folder: %s", path)
            return True
        except httpx.HTTPStatusError as exc:
            # 409 Conflict means already exists
            if exc.response.status_code == 409:
                logger.debug("Folder already exists: %s", path)
                return True
            logger.error("Failed to create folder %s: %s", path, exc)
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to create folder %s: %s", path, exc)
            raise

    def rename(self, old_path: str, new_path: str) -> bool:
        """Rename a file or directory."""
        self._random_delay()
        self._post("/rename", data={"oldPath": old_path, "newPath": new_path})
        logger.info("Renamed %s -> %s", old_path, new_path)
        return True

    def move(self, src_path: str, dst_path: str) -> bool:
        """Move a file or directory."""
        self._random_delay()
        self._post("/move", data={"srcPath": src_path, "dstPath": dst_path})
        logger.info("Moved %s -> %s", src_path, dst_path)
        return True

    def delete(self, path: str) -> bool:
        """Delete a file or directory."""
        self._random_delay()
        self._post("/delete", data={"path": path})
        logger.info("Deleted %s", path)
        return True

    def submit_offline_download(self, url: str, save_path: str) -> dict[str, Any]:
        """Submit an offline download task."""
        self._random_delay()
        result = self._post(
            "/offlineDownload",
            data={"url": url, "savePath": save_path},
        )
        task_name = result.get("taskName", "")
        status = result.get("status", "submitted")
        logger.info("Submitted offline download: url=%s save=%s task=%s", url, save_path, task_name)
        return {"task_name": task_name, "status": status}

    def get_download_status(self, task_name: str) -> dict[str, Any]:
        """Get offline download task status."""
        self._random_delay()
        result = self._get("/offlineDownload/status", params={"taskName": task_name})
        return {
            "status": result.get("status", "unknown"),
            "progress": result.get("progress", 0.0),
            "files": result.get("files", []),
        }

    def get_file_info(self, path: str) -> dict[str, Any] | None:
        """Get info for a single file. Returns None if not found."""
        self._random_delay()
        try:
            result = self._get("/fileInfo", params={"path": path})
            if not result:
                return None
            return {
                "name": result.get("name", ""),
                "path": result.get("path", path),
                "size": result.get("size", 0),
                "is_dir": result.get("isDir", False),
                "modified": result.get("modified", ""),
            }
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            self._client.close()
            self._client = None

    def __enter__(self) -> CloudDrive2Client:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"CloudDrive2Client(host={self.host!r})"
