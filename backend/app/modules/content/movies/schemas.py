from typing import Any

from pydantic import BaseModel


class MovieListResponse(BaseModel):
    """Movie list response."""

    items: list[dict[str, Any]]
    total: int
    page: int
    limit: int
    total_pages: int
