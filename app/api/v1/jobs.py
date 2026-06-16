from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.core.errors import AppError
from app.models import Backup, BackupTask, Job, User
from app.scheduler.service import reload_job, remove_job
from app.schemas.backups import BackupRunRequest, TaskCreatedResponse
from app.schemas.common import Message, Page
from app.schemas.jobs import JobCreate, JobRead, JobUpdate
from app.services.audit_service import create_audit_log
from app.services.backup_service import create_backup_task, delete_backup_record, run_backup_task

router = APIRouter()


def _run_backup_task_with_new_session(task_id: int) -> None:
    db = SessionLocal()
    try:
        run_backup_task(db, task_id)
    finally:
        db.close()


@router.get("", response_model=Page[JobRead])
def list_jobs(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("job:read")),
):
    query = db.query(Job).filter(Job.deleted_at.is_(None)).order_by(Job.id.desc())
    total = query.count()
    return {
        "items": query.offset((page - 1) * page_size).limit(page_size).all(),
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.post("", response_model=JobRead)
def create_job(
    payload: JobCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("job:write")),
):
    job = Job(**payload.model_dump(), created_by=user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    reload_job(job)
    create_audit_log(db, user=user, action="job.create", resource_type="job", resource_id=job.id, request=request)
    return job


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("job:read"))):
    job = db.get(Job, job_id)
    if not job or job.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Job not found", status_code=404)
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
    for key, value in payload.model_dump(exclude_unset=True).items():
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
def enable_job(job_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("job:write"))):
    job = db.get(Job, job_id)
    if not job or job.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Job not found", status_code=404)
    job.enabled = True
    db.commit()
    db.refresh(job)
    reload_job(job)
    return job


@router.post("/{job_id}/disable", response_model=JobRead)
def disable_job(job_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("job:write"))):
    job = db.get(Job, job_id)
    if not job or job.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Job not found", status_code=404)
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
    payload = BackupRunRequest(
        database_id=job.database_id,
        storage_id=job.storage_id,
        compression=job.backup_config.get("compression", "zstd"),
        checksum=job.backup_config.get("checksum", ["sha256"]),
        retention=job.retention_policy,
    )
    task = create_backup_task(db, payload, user, trigger_type="JOB")
    task.job_id = job.id
    db.commit()
    create_audit_log(db, user=user, action="job.run_now", resource_type="job", resource_id=job.id, request=request)
    if get_settings().run_background_tasks_inline:
        run_backup_task(db, task.id)
    else:
        background_tasks.add_task(_run_backup_task_with_new_session, task.id)
    return {"task_id": task.id, "status": task.status}
