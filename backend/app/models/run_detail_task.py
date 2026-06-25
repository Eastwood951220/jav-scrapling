from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RunDetailTaskResponse(BaseModel):
    id: str = Field(alias="_id")
    run_id: str
    task_name: str
    code: str | None = None
    source_url: str | None = None
    source_name: str | None = None
    status: str  # pending_crawl | crawled | crawl_failed | saved | save_failed
    error: str | None = None
    created_at: datetime | None = None
    crawled_at: datetime | None = None
    saved_at: datetime | None = None

    model_config = {"populate_by_name": True}


class RunDetailTaskListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
