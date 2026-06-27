from pydantic import BaseModel, Field


class TaskUrlEntry(BaseModel):
    """A single URL entry within a task."""
    url: str
    url_type: str
    has_magnet: bool = False
    has_chinese_sub: bool = False
    sort_type: int = 0
    final_url: str | None = None
    url_name: str | None = None


class TaskCreate(BaseModel):
    name: str
    urls: list[TaskUrlEntry] = Field(min_length=1)
    is_skip: bool = False


class TaskUpdate(BaseModel):
    name: str | None = None
    urls: list[TaskUrlEntry] | None = None
    is_skip: bool | None = None


class ExtractNameRequest(BaseModel):
    """提取 URL 名称的请求。"""
    url: str
    url_type: str


class ExtractNameResponse(BaseModel):
    """提取 URL 名称的响应。"""
    name: str
