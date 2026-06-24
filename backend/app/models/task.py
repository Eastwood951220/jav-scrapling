from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FilterConfigModel(BaseModel):
    only_chinese: bool = False
    exclude_multi_person: bool = False
    extra_filters: dict[str, Any] = Field(default_factory=dict)


class TaskCreate(BaseModel):
    name: str
    url: str
    url_type: str
    is_skip: bool = False
    max_list_pages: int = Field(default=50, ge=1, le=100)
    filter: FilterConfigModel = Field(default_factory=FilterConfigModel)


class TaskUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    url_type: str | None = None
    is_skip: bool | None = None
    max_list_pages: int | None = Field(None, ge=1, le=100)
    filter: FilterConfigModel | None = None


class TaskResponse(BaseModel):
    id: str
    name: str
    url: str
    url_type: str
    is_skip: bool
    max_list_pages: int
    filter: dict
    source: str | None = None
    final_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"populate_by_name": True}
