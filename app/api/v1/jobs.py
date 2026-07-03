from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.api.pagination import Pagination, pagination_params
from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.core.errors import AppError
from app.core.ownership import ensure_owner, owner_filter
from app.models import Backup, BackupTask, DatabaseInstance, Job, Storage, User
from app.scheduler.service import build_trigger, ensure_job_can_start, reload_job, remove_job
from app.schemas.backups import BackupRunRequest, TaskCreatedResponse
from app.schemas.common import Message, Page
from app.schemas.jobs import JobCreate, JobRead, JobUpdate
from app.services.audit_service import create_audit_log
from app.services.backup_service import create_backup_task, delete_backup_record, run_backup_task, try_acquire_job_slot

router = APIRouter()


def _run_backup_task_with_new_session(task_id: int) -> None:
    db = SessionLocal()
    try:
        run_backup_task(db, task_id)
    finally:
        db.close()


def _validate_job_schedule(job_like) -> None:
    try:
        build_trigger(job_like)
    except ValueError as exc:
        raise AppError("VALIDATION_ERROR", str(exc), status_code=400) from exc


@router.get("", response_model=Page[JobRead])
def list_jobs(
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("job:read")),
):
    query = db.query(Job).filter(Job.deleted_at.is_(None))
    query = owner_filter(query, Job, user).order_by(Job.id.desc())
    total = query.count()
    return {
        "items": query.offset((pagination.page - 1) * pagination.page_size).limit(pagination.page_size).all(),
        "page": pagination.page,
        "page_size": pagination.page_size,
        "total": total,
    }


@router.post("", response_model=JobRead)
def create_job(
    payload: JobCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("job:write")),
):
    database = db.get(DatabaseInstance, payload.database_id)
    if not database or database.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Database instance not found", status_code=404)
    ensure_owner(database, user, "Database instance not found")
    storage = db.get(Storage, payload.storage_id)
    if not storage or storage.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Storage not found", status_code=404)
    ensure_owner(storage, user, "Storage not found")
    job_data = payload.model_dump()
    _validate_job_schedule(SimpleNamespace(**job_data))
    job = Job(**job_data, created_by=user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    reload_job(job)
    create_audit_log(db, user=user, action="job.create", resource_type="job", resource_id=job.id, request=request)
    return job


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("job:read"))):
    job = db.get(Job, job_id)
    if not job or job.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Job not found", status_code=404)
    ensure_owner(job, user, "Job not found")
    return job


@router.put("/{job_id}", response_model=JobRead)
def update_job(
    job_id: int,
    payload: JobUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("job:write")),
):
    job = db.get(Job, job_id)
    if not job or job.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Job not found", status_code=404)
    ensure_owner(job, user, "Job not found")
    data = payload.model_dump(exclude_unset=True)
    if "database_id" in data and data["database_id"] is not None:
        database = db.get(DatabaseInstance, data["database_id"])
        if not database or database.deleted_at is not None:
            raise AppError("RESOURCE_NOT_FOUND", "Database instance not found", status_code=404)
        ensure_owner(database, user, "Database instance not found")
    if "storage_id" in data and data["storage_id"] is not None:
        storage = db.get(Storage, data["storage_id"])
        if not storage or storage.deleted_at is not None:
            raise AppError("RESOURCE_NOT_FOUND", "Storage not found", status_code=404)
        ensure_owner(storage, user, "Storage not found")
    _validate_job_schedule(SimpleNamespace(**{**job.__dict__, **data}))
    for key, value in data.items():
        setattr(job, key, value)
    db.commit()
    db.refresh(job)
    reload_job(job)
    create_audit_log(db, user=user, action="job.update", resource_type="job", resource_id=job.id, request=request)
    return job


@router.delete("/{job_id}", response_model=Message)
def delete_job(
    job_id: int,
    request: Request,
    delete_backups: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("job:write")),
):
    job = db.get(Job, job_id)
    if not job or job.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Job not found", status_code=404)
    ensure_owner(job, user, "Job not found")
    job.deleted_at = datetime.now(UTC)
    deleted_backup_ids: list[int] = []
    if delete_backups:
        backups = (
            db.query(Backup)
            .join(BackupTask, Backup.backup_task_id == BackupTask.id)
            .filter(BackupTask.job_id == job.id, Backup.deleted_at.is_(None))
            .all()
        )
        for backup in backups:
            delete_backup_record(db, backup)
            deleted_backup_ids.append(backup.id)
    db.commit()
    remove_job(job.id)
    create_audit_log(
        db,
        user=user,
        action="job.delete",
        resource_type="job",
        resource_id=job.id,
        request=request,
        metadata={"delete_backups": delete_backups, "deleted_backup_ids": deleted_backup_ids},
    )
    return {"message": "deleted"}


@router.post("/{job_id}/enable", response_model=JobRead)
def enable_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("job:write"))):
    job = db.get(Job, job_id)
    if not job or job.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Job not found", status_code=404)
    ensure_owner(job, user, "Job not found")
    _validate_job_schedule(job)
    job.enabled = True
    db.commit()
    db.refresh(job)
    reload_job(job)
    return job


@router.post("/{job_id}/disable", response_model=JobRead)
def disable_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("job:write"))):
    job = db.get(Job, job_id)
    if not job or job.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Job not found", status_code=404)
    ensure_owner(job, user, "Job not found")
    job.enabled = False
    db.commit()
    db.refresh(job)
    remove_job(job.id)
    return job


@router.post("/{job_id}/run-now", response_model=TaskCreatedResponse)
def run_job_now(
    job_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("backup:run")),
):
    job = db.get(Job, job_id)
    if not job or job.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Job not found", status_code=404)
    ensure_owner(job, user, "Job not found")
    ensure_job_can_start(db, job)
    payload = BackupRunRequest(
        database_id=job.database_id,
        storage_id=job.storage_id,
        compression=job.backup_config.get("compression", "zstd"),
        checksum=job.backup_config.get("checksum", ["sha256"]),
        retention=job.retention_policy,
    )
    task = create_backup_task(db, payload, user, trigger_type="JOB", job_id=job.id)
    if not try_acquire_job_slot(db, job, task):
        raise AppError("JOB_ALREADY_RUNNING", "Job already has a pending or running backup task", status_code=400)
    create_audit_log(db, user=user, action="job.run_now", resource_type="job", resource_id=job.id, request=request)
    if get_settings().run_background_tasks_inline:
        run_backup_task(db, task.id)
    else:
        background_tasks.add_task(_run_backup_task_with_new_session, task.id)
    return {"task_id": task.id, "status": task.status}
