from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models import Backup, BackupTask, DatabaseInstance, Storage, User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("backup:read")),
):
    today = datetime.now(UTC) - timedelta(days=1)
    return {
        "database_count": db.query(DatabaseInstance).filter(DatabaseInstance.deleted_at.is_(None)).count(),
        "storage_count": db.query(Storage).filter(Storage.deleted_at.is_(None)).count(),
        "backup_count": db.query(Backup).filter(Backup.deleted_at.is_(None)).count(),
        "backup_success_24h": db.query(BackupTask)
        .filter(BackupTask.status == "SUCCESS", BackupTask.created_at >= today)
        .count(),
        "backup_failed_24h": db.query(BackupTask)
        .filter(BackupTask.status == "FAILED", BackupTask.created_at >= today)
        .count(),
    }


@router.get("/backup-trends")
def backup_trends(
    days: int = 7,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("backup:read")),
):
    since = datetime.now(UTC) - timedelta(days=days)
    rows = (
        db.query(func.date(Backup.created_at).label("date"), Backup.status, func.count(Backup.id))
        .filter(Backup.created_at >= since)
        .group_by(func.date(Backup.created_at), Backup.status)
        .order_by(func.date(Backup.created_at).asc())
        .all()
    )
    return [{"date": str(date), "status": status, "count": count} for date, status, count in rows]


@router.get("/storage-usage")
def storage_usage(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("backup:read")),
):
    rows = (
        db.query(Backup.storage_id, func.count(Backup.id), func.coalesce(func.sum(Backup.size_bytes), 0))
        .filter(Backup.deleted_at.is_(None))
        .group_by(Backup.storage_id)
        .all()
    )
    return [
        {"storage_id": storage_id, "backup_count": backup_count, "size_bytes": size_bytes}
        for storage_id, backup_count, size_bytes in rows
    ]

