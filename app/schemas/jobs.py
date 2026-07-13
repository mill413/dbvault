from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class JobCreate(BaseModel):
    name: str
    database_id: int
    storage_id: int
    schedule_type: str
    cron_expr: str | None = None
    interval_seconds: int | None = Field(default=None, ge=5)
    run_at: datetime | None = None
    timezone: str = "Asia/Shanghai"
    enabled: bool = True
    allow_concurrent: bool = False
    retention_policy: dict[str, Any] = {}
    backup_config: dict[str, Any] = {}


class JobUpdate(BaseModel):
    name: str | None = None
    schedule_type: str | None = None
    cron_expr: str | None = None
    interval_seconds: int | None = Field(default=None, ge=5)
    run_at: datetime | None = None
    timezone: str | None = None
    enabled: bool | None = None
    allow_concurrent: bool | None = None
    retention_policy: dict[str, Any] | None = None
    backup_config: dict[str, Any] | None = None


class JobRead(ORMModel):
    id: int
    name: str
    database_id: int
    storage_id: int
    schedule_type: str
    cron_expr: str | None = None
    interval_seconds: int | None = None
    run_at: datetime | None = None
    timezone: str
    enabled: bool
    allow_concurrent: bool
    retention_policy: dict[str, Any]
    backup_config: dict[str, Any]
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    last_status: str | None = None
    skipped_count: int
    created_by: int | None = None
    created_by_username: str | None = None
    created_at: datetime
    updated_at: datetime
