from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog, TaskEvent, User


def create_audit_log(
    db: Session,
    *,
    user: User | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | int | None = None,
    request: Request | None = None,
    result: str = "success",
    reason: str | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    audit = AuditLog(
        actor_user_id=user.id if user else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        request_id=getattr(request.state, "request_id", None) if request else None,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
        result=result,
        reason=reason,
        extra_metadata=metadata or {},
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit


def add_task_event(
    db: Session,
    *,
    task_type: str,
    task_id: int,
    level: str,
    message: str,
    phase: str | None = None,
    metadata: dict | None = None,
) -> TaskEvent:
    event = TaskEvent(
        task_type=task_type,
        task_id=task_id,
        level=level,
        phase=phase,
        message=message,
        extra_metadata=metadata or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

