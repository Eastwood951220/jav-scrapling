from typing import Any

from pydantic import BaseModel


class RunDetailTaskListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
