from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Alert, User
from app.schemas.alerts import AlertRead
from app.schemas.common import Page

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=Page[AlertRead])
def list_alerts(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("backup:read")),
):
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status)
    total = query.count()
    items = query.order_by(Alert.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.post("/{alert_id}/resolve", response_model=AlertRead)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("backup:run")),
):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise AppError("RESOURCE_NOT_FOUND", "Alert not found", status_code=404)
    alert.status = "RESOLVED"
    alert.resolved_at = datetime.now(UTC)
    db.commit()
    db.refresh(alert)
    return alert

