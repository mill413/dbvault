from sqlalchemy.orm import Session

from app.models import Alert


def create_alert(
    db: Session,
    *,
    alert_type: str,
    severity: str,
    resource_type: str | None,
    resource_id: str | int | None,
    title: str,
    message: str,
    dedupe_key: str | None = None,
) -> Alert:
    if dedupe_key:
        existing = (
            db.query(Alert)
            .filter(Alert.dedupe_key == dedupe_key, Alert.status == "OPEN")
            .order_by(Alert.created_at.desc())
            .first()
        )
        if existing:
            return existing
    alert = Alert(
        alert_type=alert_type,
        severity=severity,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        title=title,
        message=message,
        dedupe_key=dedupe_key,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert

