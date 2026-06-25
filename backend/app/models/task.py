from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    name: str
    url: str
    url_type: str
    is_skip: bool = False
    max_list_pages: int = Field(default=50, ge=1, le=100)


class TaskUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    url_type: str | None = None
    is_skip: bool | None = None
    max_list_pages: int | None = Field(None, ge=1, le=100)

