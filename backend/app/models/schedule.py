from datetime import datetime

from pydantic import BaseModel, Field


class ScheduleCreate(BaseModel):
    name: str
    task_ids: list[str] = Field(default_factory=list)
    cron_expression: str = "0 2 * * *"
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    name: str | None = None
    task_ids: list[str] | None = None
    cron_expression: str | None = None
    enabled: bool | None = None
