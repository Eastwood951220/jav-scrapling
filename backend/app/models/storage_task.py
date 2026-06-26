from datetime import datetime

from pydantic import BaseModel, Field


class StorageTask(BaseModel):
    """Record of a CloudDrive2 file operation."""

    movie_code: str
    source_path: str
    target_path: str
    status: str = "pending"  # pending, downloading, moving, completed, failed
    progress: float = 0.0
    error_message: str | None = None
    retry_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
