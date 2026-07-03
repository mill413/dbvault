from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.api.pagination import Pagination, pagination_params
from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.core.errors import AppError
from app.core.ownership import ensure_owner, owner_filter
from app.models import RestoreTask, TaskEvent, User
from app.schemas.audit import TaskEventRead
from app.schemas.backups import TaskCreatedResponse
from app.schemas.common import Page
from app.schemas.restores import RestoreDryRunResponse, RestoreRunRequest, RestoreTaskRead
from app.services.audit_service import create_audit_log
from app.services.restore_service import create_restore_task, dry_run_restore, run_restore_task

router = APIRouter()


def _run_restore_task_with_new_session(task_id: int) -> None:
    db = SessionLocal()
    try:
        run_restore_task(db, task_id)
    finally:
        db.close()


@router.post("/restore/dry-run", response_model=RestoreDryRunResponse)
def dry_run(
    payload: RestoreRunRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("backup:read")),
):
    result = dry_run_restore(db, payload.backup_id, payload.target_database_id, user, payload.restore_mode)
    create_audit_log(
        db,
        user=user,
        action="restore.dry_run",
        resource_type="backup",
        resource_id=payload.backup_id,
        request=request,
        result="success" if result["ok"] else "failed",
        reason=result["message"],
        metadata={
            "target_database_id": payload.target_database_id,
            "restore_mode": payload.restore_mode,
        },
    )
    return result


@router.post("/restore/run", response_model=TaskCreatedResponse)
def run_restore(
    payload: RestoreRunRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("restore:run")),
):
    task = create_restore_task(db, payload, user)
    create_audit_log(
        db,
        user=user,
        action="restore.run",
        resource_type="restore_task",
        resource_id=task.id,
        request=request,
    )
    if get_settings().run_background_tasks_inline:
        run_restore_task(db, task.id)
    else:
        background_tasks.add_task(_run_restore_task_with_new_session, task.id)
    return {"task_id": task.id, "status": task.status}


@router.get("/restore-tasks", response_model=Page[RestoreTaskRead])
def list_restore_tasks(
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("backup:read")),
):
    query = db.query(RestoreTask)
    query = owner_filter(query, RestoreTask, user).order_by(RestoreTask.created_at.desc())
    total = query.count()
    return {
        "items": query.offset((pagination.page - 1) * pagination.page_size).limit(pagination.page_size).all(),
        "page": pagination.page,
        "page_size": pagination.page_size,
        "total": total,
    }


@router.get("/restore-tasks/{task_id}", response_model=RestoreTaskRead)
def get_restore_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("backup:read")),
):
    task = db.get(RestoreTask, task_id)
    if not task:
        raise AppError("RESOURCE_NOT_FOUND", "Restore task not found", status_code=404)
    ensure_owner(task, user, "Restore task not found")
    return task


@router.get("/restore-tasks/{task_id}/events", response_model=list[TaskEventRead])
def get_restore_task_events(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("backup:read")),
):
    task = db.get(RestoreTask, task_id)
    if not task:
        raise AppError("RESOURCE_NOT_FOUND", "Restore task not found", status_code=404)
    ensure_owner(task, user, "Restore task not found")
    return (
        db.query(TaskEvent)
        .filter(TaskEvent.task_type == "restore", TaskEvent.task_id == task_id)
        .order_by(TaskEvent.id.asc())
        .all()
    )
