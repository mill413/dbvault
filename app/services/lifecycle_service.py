from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.ownership import owner_filter
from app.models import Backup, DatabaseInstance, Storage, User
from app.services.audit_service import add_task_event
from app.services.storage_service import build_storage_driver


def calculate_expires_at(retention: dict) -> datetime | None:
    keep_days = retention.get("keep_days")
    delete_after_days = retention.get("delete_after_days")
    days = delete_after_days or keep_days
    if not days:
        return None
    return datetime.now(UTC) + timedelta(days=int(days))


def expired_backup_candidates(db: Session, user: User | None = None) -> list[Backup]:
    now = datetime.now(UTC)
    query = db.query(Backup).filter(
        Backup.deleted_at.is_(None),
        Backup.status == "AVAILABLE",
        Backup.expires_at.is_not(None),
        Backup.expires_at <= now,
    )
    if user is not None:
        query = owner_filter(query, Backup, user)
    return query.all()


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


def run_lifecycle_cleanup(db: Session, *, dry_run: bool = False, user: User | None = None) -> dict:
    candidates = expired_backup_candidates(db, user=user)
    deleted: list[int] = []
    failed: list[dict] = []
    for backup in candidates:
        if dry_run:
            deleted.append(backup.id)
            continue
        backup.status = "DELETING"
        db.commit()
        try:
            storage = db.get(Storage, backup.storage_id)
            if not storage:
                raise AppError("RESOURCE_NOT_FOUND", "Storage not found", status_code=404)
            build_storage_driver(storage).delete(backup.object_key)
            backup.status = "DELETED"
            backup.deleted_at = datetime.now(UTC)
            db.commit()
            deleted.append(backup.id)
        except Exception as exc:
            backup.status = "AVAILABLE"
            db.commit()
            failed.append({"backup_id": backup.id, "message": str(exc)})
            add_task_event(
                db,
                task_type="lifecycle",
                task_id=backup.id,
                level="ERROR",
                message=str(exc),
            )
    return {
        "dry_run": dry_run,
        "candidate_count": len(candidates),
        "deleted_backup_ids": deleted,
        "failed": failed,
    }
