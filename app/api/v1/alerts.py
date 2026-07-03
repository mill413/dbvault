from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.api.pagination import Pagination, pagination_params
from app.core.database import get_db
from app.core.errors import AppError
from app.core.ownership import alert_owner_filter, is_admin
from app.models import Alert, User
from app.schemas.alerts import AlertRead
from app.schemas.common import Page

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=Page[AlertRead])
def list_alerts(
    pagination: Pagination = Depends(pagination_params),
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("backup:read")),
):
    query = db.query(Alert)
    query = alert_owner_filter(query, user)
    if status:
        query = query.filter(Alert.status == status)
    total = query.count()
    items = (
        query.order_by(Alert.created_at.desc())
        .offset((pagination.page - 1) * pagination.page_size)
        .limit(pagination.page_size)
        .all()
    )
    return {"items": items, "page": pagination.page, "page_size": pagination.page_size, "total": total}


@router.post("/{alert_id}/resolve", response_model=AlertRead)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("backup:run")),
):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise AppError("RESOURCE_NOT_FOUND", "Alert not found", status_code=404)
    if not is_admin(user):
        visible = alert_owner_filter(db.query(Alert).filter(Alert.id == alert_id), user).first()
        if not visible:
            raise AppError("RESOURCE_NOT_FOUND", "Alert not found", status_code=404)
    alert.status = "RESOLVED"
    alert.resolved_at = datetime.now(UTC)
    db.commit()
    db.refresh(alert)
    return alert
