from pydantic import BaseModel, Field


class SettingUpdate(BaseModel):
    MAX_LIST_PAGES: int | None = Field(None, ge=1, le=100)
    LIST_PAGE_DELAY_MIN: float | None = Field(None, ge=0)
    LIST_PAGE_DELAY_MAX: float | None = Field(None, ge=0)
    DETAIL_PAGE_DELAY_MIN: float | None = Field(None, ge=0)
    DETAIL_PAGE_DELAY_MAX: float | None = Field(None, ge=0)
    SECURITY_WAIT_SECONDS: float | None = Field(None, ge=0)
    REQUEST_TIMEOUT: int | None = Field(None, ge=1)
    USE_DYNAMIC_FETCHER: bool | None = None
    MONGO_URI: str | None = None
    MONGO_DB_NAME: str | None = None
    MONGO_CONNECT_TIMEOUT_MS: int | None = Field(None, ge=1000)
