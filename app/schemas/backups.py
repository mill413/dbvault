from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.common import ORMModel


class BackupRunRequest(BaseModel):
    database_id: int
    storage_id: int | None = None
    compression: str = "zstd"
    checksum: list[str] = ["sha256"]
    retention: dict[str, Any] = {}


class BackupUploadResponse(BaseModel):
    backup_id: int
    status: str


class TaskCreatedResponse(BaseModel):
    task_id: int
    status: str


class BackupRead(ORMModel):
    id: int
    database_id: int
    storage_id: int
    backup_task_id: int | None = None
    source_type: str
    backup_type: str
    status: str
    object_key: str
    filename: str
    file_format: str
    size_bytes: int
    compressed: bool
    compression: str | None = None
    md5: str | None = None
    sha256: str
    database_version: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime


class BackupTaskRead(ORMModel):
    id: int
    database_id: int
    storage_id: int
    job_id: int | None = None
    status: str
    phase: str | None = None
    trigger_type: str
    progress: int
    error_code: str | None = None
    error_message: str | None = None
    stdout_tail: str | None = None
    stderr_tail: str | None = None
    size_bytes: int | None = None
    duration_seconds: float | None = None
    created_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None


class VerifyResponse(BaseModel):
    ok: bool
    expected_sha256: str
    actual_sha256: str


class LifecycleCleanupResponse(BaseModel):
    dry_run: bool
    candidate_count: int
    deleted_backup_ids: list[int]
    failed: list[dict]
