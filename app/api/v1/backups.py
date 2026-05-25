from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.core.errors import AppError
from app.models import Backup, BackupTask, TaskEvent, User
from app.schemas.audit import TaskEventRead
from app.schemas.backups import (
    BackupRead,
    BackupRunRequest,
    BackupTaskRead,
    BackupUploadResponse,
    LifecycleCleanupResponse,
    TaskCreatedResponse,
    VerifyResponse,
)
from app.schemas.common import Message, Page
from app.services.audit_service import create_audit_log
from app.services.backup_service import (
    create_backup_task,
    run_backup_task,
    upload_backup_file,
    verify_backup,
)
from app.services.lifecycle_service import run_lifecycle_cleanup
from app.services.storage_service import build_storage_driver

router = APIRouter()


def _run_backup_task_with_new_session(task_id: int) -> None:
    db = SessionLocal()
    try:
        run_backup_task(db, task_id)
    finally:
        db.close()


@router.post("/backups/run", response_model=TaskCreatedResponse)
def run_backup(
    payload: BackupRunRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("backup:run")),
):
    task = create_backup_task(db, payload, user)
    create_audit_log(
        db,
        user=user,
        action="backup.run",
        resource_type="backup_task",
        resource_id=task.id,
        request=request,
    )
    if get_settings().run_background_tasks_inline:
        run_backup_task(db, task.id)
    else:
        background_tasks.add_task(_run_backup_task_with_new_session, task.id)
    return {"task_id": task.id, "status": task.status}


@router.post("/backups/upload", response_model=BackupUploadResponse)
def upload_backup(
    request: Request,
    database_id: int,
    file: UploadFile = File(...),
    storage_id: int | None = None,
    compression: str = "none",
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("backup:run")),
):
    backup = upload_backup_file(
        db,
        database_id=database_id,
        storage_id=storage_id,
        file=file,
        compression=compression,
        user=user,
    )
    create_audit_log(
        db,
        user=user,
        action="backup.upload",
        resource_type="backup",
        resource_id=backup.id,
        request=request,
    )
    return {"backup_id": backup.id, "status": backup.status}


@router.post("/backups/lifecycle/run", response_model=LifecycleCleanupResponse)
def run_lifecycle_cleanup_endpoint(
    dry_run: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("backup:delete")),
):
    return run_lifecycle_cleanup(db, dry_run=dry_run)


@router.get("/backups", response_model=Page[BackupRead])
def list_backups(
    page: int = 1,
    page_size: int = 20,
    database_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("backup:read")),
):
    query = db.query(Backup).filter(Backup.deleted_at.is_(None))
    if database_id:
        query = query.filter(Backup.database_id == database_id)
    if status:
        query = query.filter(Backup.status == status)
    total = query.count()
    items = query.order_by(Backup.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/backups/{backup_id}", response_model=BackupRead)
def get_backup(backup_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("backup:read"))):
    item = db.get(Backup, backup_id)
    if not item or item.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Backup not found", status_code=404)
    return item


@router.get("/backups/{backup_id}/download")
def download_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("backup:read")),
):
    backup = db.get(Backup, backup_id)
    if not backup or backup.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Backup not found", status_code=404)
    storage = backup.storage
    local_path = get_settings().backup_tmp_dir / f"download-{backup.id}-{backup.filename}"
    build_storage_driver(storage).download(backup.object_key, local_path)
    return FileResponse(local_path, filename=backup.filename)


@router.post("/backups/{backup_id}/verify", response_model=VerifyResponse)
def verify_backup_endpoint(
    backup_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("backup:run")),
):
    backup = db.get(Backup, backup_id)
    if not backup or backup.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Backup not found", status_code=404)
    return verify_backup(db, backup)


@router.delete("/backups/{backup_id}", response_model=Message)
def delete_backup(
    backup_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("backup:delete")),
):
    backup = db.get(Backup, backup_id)
    if not backup or backup.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Backup not found", status_code=404)
    backup.status = "DELETING"
    db.commit()
    build_storage_driver(backup.storage).delete(backup.object_key)
    backup.status = "DELETED"
    backup.deleted_at = datetime.now(UTC)
    db.commit()
    create_audit_log(
        db,
        user=user,
        action="backup.delete",
        resource_type="backup",
        resource_id=backup.id,
        request=request,
    )
    return {"message": "deleted"}


@router.get("/backup-tasks", response_model=Page[BackupTaskRead])
def list_backup_tasks(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("backup:read")),
):
    query = db.query(BackupTask).order_by(BackupTask.created_at.desc())
    total = query.count()
    return {
        "items": query.offset((page - 1) * page_size).limit(page_size).all(),
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/backup-tasks/{task_id}", response_model=BackupTaskRead)
def get_backup_task(task_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("backup:read"))):
    task = db.get(BackupTask, task_id)
    if not task:
        raise AppError("RESOURCE_NOT_FOUND", "Backup task not found", status_code=404)
    return task


@router.get("/backup-tasks/{task_id}/events", response_model=list[TaskEventRead])
def get_backup_task_events(
    task_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("backup:read")),
):
    return (
        db.query(TaskEvent)
        .filter(TaskEvent.task_type == "backup", TaskEvent.task_id == task_id)
        .order_by(TaskEvent.id.asc())
        .all()
    )


@router.post("/backup-tasks/{task_id}/cancel", response_model=BackupTaskRead)
def cancel_backup_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("backup:run")),
):
    task = db.get(BackupTask, task_id)
    if not task:
        raise AppError("RESOURCE_NOT_FOUND", "Backup task not found", status_code=404)
    if task.status not in {"PENDING", "RUNNING"}:
        raise AppError("VALIDATION_ERROR", "Task cannot be cancelled", status_code=400)
    task.status = "CANCELLED"
    task.ended_at = datetime.now(UTC)
    db.commit()
    db.refresh(task)
    return task
