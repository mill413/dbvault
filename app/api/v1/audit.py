from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models import AuditLog, User
from app.schemas.audit import AuditLogRead
from app.schemas.common import Page

router = APIRouter()


@router.get("/audit-logs", response_model=Page[AuditLogRead])
def list_audit_logs(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("audit:read")),
):
    query = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    total = query.count()
    return {
        "items": query.offset((page - 1) * page_size).limit(page_size).all(),
        "page": page,
        "page_size": page_size,
        "total": total,
    }

