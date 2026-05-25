from datetime import datetime
from typing import Any

from app.schemas.common import ORMModel


class AuditLogRead(ORMModel):
    id: int
    actor_user_id: int | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    request_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    result: str
    reason: str | None = None
    extra_metadata: dict[str, Any]
    created_at: datetime


class TaskEventRead(ORMModel):
    id: int
    task_type: str
    task_id: int
    level: str
    phase: str | None = None
    message: str
    extra_metadata: dict[str, Any]
    created_at: datetime

