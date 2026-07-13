from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import Backup, BackupTask, Job, RestoreTask, TaskEvent

INTERRUPTED_STATUSES = {"PENDING", "RUNNING"}


def recover_interrupted_tasks(db: Session) -> dict[str, int]:
    now = datetime.now(UTC)
    backup_count = 0
    restore_count = 0

    backup_tasks = db.query(BackupTask).filter(BackupTask.status.in_(INTERRUPTED_STATUSES)).all()
    for task in backup_tasks:
        task.status = "FAILED"
        task.error_code = "TASK_INTERRUPTED"
        task.error_message = "Task was interrupted by service shutdown or restart"
        task.ended_at = now
        backup = db.query(Backup).filter(Backup.backup_task_id == task.id).first()
        if backup:
            backup.status = "FAILED"
            backup.completed_at = now
        db.add(
            TaskEvent(
                task_type="backup",
                task_id=task.id,
                level="ERROR",
                phase=task.phase,
                message=task.error_message,
                extra_metadata={"recovered": True},
            )
        )
        backup_count += 1

    restore_tasks = db.query(RestoreTask).filter(RestoreTask.status.in_(INTERRUPTED_STATUSES)).all()
    for task in restore_tasks:
        task.status = "FAILED"
        task.error_code = "TASK_INTERRUPTED"
        task.error_message = "Task was interrupted by service shutdown or restart"
        task.ended_at = now
        db.add(
            TaskEvent(
                task_type="restore",
                task_id=task.id,
                level="ERROR",
                phase=task.phase,
                message=task.error_message,
                extra_metadata={"recovered": True},
            )
        )
        restore_count += 1

    active_task_ids = [task.id for task in backup_tasks]
    if active_task_ids:
        db.query(Job).filter(Job.active_backup_task_id.in_(active_task_ids)).update(
            {Job.active_backup_task_id: None},
            synchronize_session=False,
        )

    db.commit()
    return {"backup_tasks": backup_count, "restore_tasks": restore_count}
