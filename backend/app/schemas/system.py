from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SystemOverview(BaseModel):
    status: Literal["ok", "degraded"]
    app_version: str
    environment: str
    database_status: Literal["ok", "error"]
    upload_status: Literal["ok", "error"]
    upload_free_bytes: int | None
    log_file_enabled: bool
    log_size_bytes: int
    uptime_seconds: int
    checked_at: datetime


class SystemLogEntry(BaseModel):
    timestamp: datetime
    level: str
    logger: str
    message: str
    context: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    exception_type: str | None = None


class SystemLogPage(BaseModel):
    items: list[SystemLogEntry]
    returned: int
