from typing import Any

from pydantic import BaseModel


class RunDetailTaskListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int = 1
    limit: int = 20
    total_pages: int = 1
