from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.core.ownership import alert_owner_filter, owner_filter
from app.models import Alert, Backup, BackupTask, DatabaseInstance, Job, Storage, User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("backup:read")),
):
    today = datetime.now(UTC) - timedelta(days=1)
    return {
        "database_count": owner_filter(
            db.query(DatabaseInstance).filter(DatabaseInstance.deleted_at.is_(None)), DatabaseInstance, user
        ).count(),
        "storage_count": owner_filter(db.query(Storage).filter(Storage.deleted_at.is_(None)), Storage, user).count(),
        "backup_count": owner_filter(db.query(Backup).filter(Backup.deleted_at.is_(None)), Backup, user).count(),
        "job_count": owner_filter(
            db.query(Job).filter(Job.deleted_at.is_(None), Job.enabled.is_(True)), Job, user
        ).count(),
        "alert_count": alert_owner_filter(db.query(Alert).filter(Alert.status == "OPEN"), user).count(),
        "backup_success_24h": owner_filter(
            db.query(BackupTask).filter(BackupTask.status == "SUCCESS", BackupTask.created_at >= today),
            BackupTask,
            user,
        ).count(),
        "backup_failed_24h": owner_filter(
            db.query(BackupTask).filter(BackupTask.status == "FAILED", BackupTask.created_at >= today),
            BackupTask,
            user,
        ).count(),
    }


@router.get("/backup-trends")
def backup_trends(
    days: int = 7,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("backup:read")),
):
    since = datetime.now(UTC) - timedelta(days=days)
    day_expr = func.date(BackupTask.created_at)
    query = db.query(
        day_expr.label("day"),
        BackupTask.status,
        func.count(BackupTask.id),
    ).filter(BackupTask.created_at >= since)
    query = owner_filter(query, BackupTask, user)
    rows = (
        query.group_by(day_expr, BackupTask.status)
        .order_by(day_expr.asc())
        .all()
    )
    if not rows:
        return []

    grouped: dict[str, dict] = defaultdict(lambda: {"success_count": 0, "failed_count": 0})
    for d, status, count in rows:
        key = d.isoformat() if isinstance(d, date) else str(d)
        if status == "SUCCESS":
            grouped[key]["success_count"] = count
        elif status == "FAILED":
            grouped[key]["failed_count"] = count

    all_dates: set[str] = set()
    for i in range(days):
        all_dates.add(str(date.today() - timedelta(days=i)))
    for d in all_dates:
        if d not in grouped:
            grouped[d] = {"success_count": 0, "failed_count": 0}

    return [
        {"date": d, **counts}
        for d, counts in sorted(grouped.items())
    ]


@router.get("/storage-usage")
def storage_usage(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("backup:read")),
):
    query = (
        db.query(Storage.name, func.count(Backup.id), func.coalesce(func.sum(Backup.size_bytes), 0))
        .join(Backup, Backup.storage_id == Storage.id)
        .filter(Storage.deleted_at.is_(None), Backup.deleted_at.is_(None))
    )
    query = owner_filter(query, Storage, user)
    rows = query.group_by(Storage.id, Storage.name).all()
    return [
        {"storage_name": storage_name, "backup_count": backup_count, "used_bytes": used_bytes}
        for storage_name, backup_count, used_bytes in rows
    ]
