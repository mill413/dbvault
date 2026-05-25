from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Backup, DatabaseInstance


def calculate_expires_at(retention: dict) -> datetime | None:
    keep_days = retention.get("keep_days")
    delete_after_days = retention.get("delete_after_days")
    days = delete_after_days or keep_days
    if not days:
        return None
    return datetime.now(UTC) + timedelta(days=int(days))


def expired_backup_candidates(db: Session) -> list[Backup]:
    now = datetime.now(UTC)
    return (
        db.query(Backup)
        .filter(
            Backup.deleted_at.is_(None),
            Backup.status == "AVAILABLE",
            Backup.expires_at.is_not(None),
            Backup.expires_at <= now,
        )
        .all()
    )


def latest_successful_backup(db: Session, instance: DatabaseInstance) -> Backup | None:
    return (
        db.query(Backup)
        .filter(
            Backup.database_id == instance.id,
            Backup.status == "AVAILABLE",
            Backup.deleted_at.is_(None),
        )
        .order_by(Backup.created_at.desc())
        .first()
    )

