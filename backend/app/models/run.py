from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RunLogEntry(BaseModel):
    timestamp: datetime
    level: str = "INFO"
    message: str


class RunResponse(BaseModel):
    id: str = Field(alias="_id")
    task_id: str
    task_name: str | None = None
    status: str  # queued | running | completed | failed
    queued_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    logs: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class RunListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    limit: int
    total_pages: int


class QueueStatusResponse(BaseModel):
    queue_size: int
    is_running: bool
    current_run_id: str | None = None
    stop_requested: bool = False
