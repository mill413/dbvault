from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.common import ORMModel


class RestoreRunRequest(BaseModel):
    backup_id: int
    target_database_id: int | None = None
    restore_mode: Literal["NEW_INSTANCE", "ORIGINAL_INSTANCE"] = "NEW_INSTANCE"
    dry_run: bool = False
    confirm_text: str | None = None


class RestoreDryRunResponse(BaseModel):
    ok: bool
    checks: dict[str, bool]
    message: str


class RestoreTaskRead(ORMModel):
    id: int
    backup_id: int
    source_database_id: int | None = None
    target_database_id: int | None = None
    restore_mode: str
    status: str
    phase: str | None = None
    dry_run: bool
    progress: int
    error_code: str | None = None
    error_message: str | None = None
    stdout_tail: str | None = None
    stderr_tail: str | None = None
    duration_seconds: float | None = None
    created_by: int | None = None
    created_by_username: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None
