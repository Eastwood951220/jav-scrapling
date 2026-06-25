from typing import Any

from pydantic import BaseModel, Field


class MovieListQuery(BaseModel):
    """Movie list query parameters."""

    search: str | None = None
    source_task_name: str | None = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    sort_by: str = "created_at"
    sort_order: int = -1  # -1 desc, 1 asc


class MovieListResponse(BaseModel):
    """Movie list response."""

    items: list[dict[str, Any]]
    total: int
    page: int
    limit: int
    total_pages: int
