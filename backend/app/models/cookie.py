from datetime import datetime

from pydantic import BaseModel, Field


class CookieFileInfo(BaseModel):
    """Metadata about a cookie file."""
    filename: str
    size_bytes: int
    created_at: datetime | None = None


class CookieContent(BaseModel):
    """Cookie key-value pairs loaded from a file."""
    filename: str
    cookies: dict[str, str]


class CookieUpdate(BaseModel):
    """Request body for creating or updating a cookie file.

    Accepts either a flat dict of key-value pairs, or a list of
    {name, value} objects (Netscape-like format). Both are normalized
    into the dict format by the API layer before saving.
    """
    cookies: dict[str, str] | list[dict[str, str]]

    class Config:
        json_schema_extra = {
            "examples": [
                {"cookies": {"session": "abc123", "token": "xyz789"}},
                {"cookies": [{"name": "session", "value": "abc123"}]},
            ]
        }
