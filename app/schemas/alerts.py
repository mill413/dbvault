from datetime import datetime

from app.schemas.common import ORMModel


class AlertRead(ORMModel):
    id: int
    alert_type: str
    severity: str
    resource_type: str | None = None
    resource_id: str | None = None
    title: str
    message: str
    status: str
    dedupe_key: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None

