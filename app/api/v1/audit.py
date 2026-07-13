from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.api.pagination import Pagination, pagination_params
from app.core.database import get_db
from app.models import AuditLog, User
from app.schemas.audit import AuditLogRead
from app.schemas.common import Page

router = APIRouter()


@router.get("/audit-logs", response_model=Page[AuditLogRead])
def list_audit_logs(
    pagination: Pagination = Depends(pagination_params),
    action: str | None = None,
    result: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("audit:read")),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if result:
        query = query.filter(AuditLog.result == result)
    query = query.order_by(AuditLog.created_at.desc())
    total = query.count()
    return {
        "items": query.offset((pagination.page - 1) * pagination.page_size).limit(pagination.page_size).all(),
        "page": pagination.page,
        "page_size": pagination.page_size,
        "total": total,
    }
