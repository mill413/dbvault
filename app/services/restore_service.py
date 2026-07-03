import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.ownership import ensure_owner
from app.drivers.registry import registry
from app.models import Backup, DatabaseInstance, RestoreTask, Storage, User
from app.services.alert_service import create_alert
from app.services.audit_service import add_task_event
from app.services.database_service import build_database_driver
from app.services.storage_service import build_storage_driver
from app.utils.checksum import file_checksum
from app.utils.paths import safe_join

RESTORE_MODES = {"NEW_INSTANCE", "ORIGINAL_INSTANCE"}


def _validate_restore_mode(restore_mode: str) -> None:
    if restore_mode not in RESTORE_MODES:
        raise AppError("VALIDATION_ERROR", "Unsupported restore mode", status_code=400)


def _target_matches_backup_type(backup: Backup | None, target: DatabaseInstance | None) -> bool:
    if not backup or not target or not backup.database:
        return False
    return backup.database.db_type == target.db_type


def _target_has_active_restore(db: Session, target_database_id: int, exclude_task_id: int | None = None) -> bool:
    query = db.query(RestoreTask).filter(
        RestoreTask.target_database_id == target_database_id,
        RestoreTask.status.in_(["PENDING", "RUNNING"]),
    )
    if exclude_task_id is not None:
        query = query.filter(RestoreTask.id != exclude_task_id)
    return query.first() is not None


def dry_run_restore(
    db: Session,
    backup_id: int,
    target_database_id: int | None,
    user: User,
    restore_mode: str = "NEW_INSTANCE",
) -> dict:
    _validate_restore_mode(restore_mode)
    backup = db.get(Backup, backup_id)
    target = db.get(DatabaseInstance, target_database_id) if target_database_id else None
    effective_target = target
    if restore_mode == "ORIGINAL_INSTANCE" and backup is not None and target_database_id is None:
        effective_target = backup.database
    storage = db.get(Storage, backup.storage_id) if backup else None
    backup_owner_ok = False
    target_owner_ok = False
    if backup is not None and backup.deleted_at is None:
        try:
            ensure_owner(backup, user, "Backup not found")
            backup_owner_ok = True
        except AppError:
            backup_owner_ok = False
    if restore_mode == "NEW_INSTANCE" and target_database_id is None:
        target_owner_ok = False
    elif target_database_id:
        if target is not None and target.deleted_at is None:
            try:
                ensure_owner(target, user, "Target database not found")
                target_owner_ok = True
            except AppError:
                target_owner_ok = False
        if backup is not None and target_database_id == backup.database_id and restore_mode == "NEW_INSTANCE":
            target_owner_ok = False
    else:
        target_owner_ok = True
    checks = {
        "backup_exists": backup is not None and backup.deleted_at is None and backup_owner_ok,
        "backup_available": bool(backup and backup_owner_ok and backup.status == "AVAILABLE"),
        "storage_exists": storage is not None and backup_owner_ok,
        "target_exists": target_owner_ok,
        "target_type_matches": bool(target_owner_ok and _target_matches_backup_type(backup, effective_target)),
        "target_not_busy": bool(
            effective_target and not _target_has_active_restore(db, effective_target.id)
        ),
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "message": "Restore dry-run passed" if all(checks.values()) else "Restore dry-run failed",
    }


def create_restore_task(db: Session, payload, user: User) -> RestoreTask:
    _validate_restore_mode(payload.restore_mode)
    backup = db.get(Backup, payload.backup_id)
    if not backup or backup.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Backup not found", status_code=404)
    ensure_owner(backup, user, "Backup not found")
    if backup.status != "AVAILABLE":
        raise AppError("VALIDATION_ERROR", "Backup is not available", status_code=400)
    if payload.restore_mode == "NEW_INSTANCE":
        if payload.target_database_id is None:
            raise AppError("VALIDATION_ERROR", "Target database is required for new instance restore", status_code=400)
        if payload.target_database_id == backup.database_id:
            raise AppError(
                "VALIDATION_ERROR",
                "Target database must be different from source database",
                status_code=400,
            )
    if payload.restore_mode == "ORIGINAL_INSTANCE" and payload.target_database_id not in {None, backup.database_id}:
        raise AppError("VALIDATION_ERROR", "Original instance restore must target the source database", status_code=400)
    target_id = payload.target_database_id or backup.database_id
    target = db.get(DatabaseInstance, target_id) if target_id else None
    if not target or target.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Target database not found", status_code=404)
    ensure_owner(target, user, "Target database not found")
    if backup.database is None or backup.database.db_type != target.db_type:
        raise AppError("VALIDATION_ERROR", "Target database type must match backup source type", status_code=400)
    if _target_has_active_restore(db, target.id):
        raise AppError(
            "RESTORE_TARGET_BUSY",
            "Target database already has a pending or running restore",
            status_code=400,
        )
    if payload.restore_mode == "ORIGINAL_INSTANCE":
        expected = f"restore {backup.database.name}" if backup.database else f"restore {backup.database_id}"
        if payload.confirm_text != expected:
            raise AppError("CONFIRM_TEXT_INVALID", "Invalid restore confirmation text", status_code=400)
    task = RestoreTask(
        backup_id=backup.id,
        source_database_id=backup.database_id,
        target_database_id=payload.target_database_id or backup.database_id,
        restore_mode=payload.restore_mode,
        status="PENDING",
        dry_run=payload.dry_run,
        confirm_text=payload.confirm_text,
        created_by=user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    add_task_event(db, task_type="restore", task_id=task.id, level="INFO", message="Restore task created")
    return task


def run_restore_task(db: Session, task_id: int) -> RestoreTask:
    settings = get_settings()
    task = db.get(RestoreTask, task_id)
    if not task:
        raise AppError("RESOURCE_NOT_FOUND", "Restore task not found", status_code=404)
    claimed = (
        db.query(RestoreTask)
        .filter(RestoreTask.id == task_id, RestoreTask.status == "PENDING")
        .update(
            {
                RestoreTask.status: "RUNNING",
                RestoreTask.started_at: datetime.now(UTC),
            },
            synchronize_session=False,
        )
    )
    if not claimed:
        db.rollback()
        db.refresh(task)
        return task
    db.commit()
    db.refresh(task)
    if task.dry_run:
        task.status = "SUCCESS"
        task.progress = 100
        task.ended_at = datetime.now(UTC)
        db.commit()
        return task

    start = monotonic()
    task.phase = "DOWNLOADING"
    task.progress = 10
    db.commit()
    work_dir = Path(tempfile.mkdtemp(prefix=f"restore-{task.id}-", dir=settings.backup_tmp_dir))
    try:
        backup = db.get(Backup, task.backup_id)
        storage = db.get(Storage, backup.storage_id) if backup else None
        target = db.get(DatabaseInstance, task.target_database_id) if task.target_database_id else None
        if not backup or not storage or not target:
            raise AppError("RESOURCE_NOT_FOUND", "Restore resource not found", status_code=404)
        local_path = safe_join(work_dir, backup.filename)
        build_storage_driver(storage).download(backup.object_key, local_path)

        task.phase = "VERIFYING"
        task.progress = 35
        db.commit()
        actual = file_checksum(local_path, "sha256")
        if actual != backup.sha256:
            raise AppError("CHECKSUM_MISMATCH", "Backup checksum mismatch", status_code=500)

        restore_file = local_path
        if backup.compressed and backup.compression:
            task.phase = "DECOMPRESSING"
            task.progress = 55
            db.commit()
            compression_cls = registry.get_compression(backup.compression)
            restore_file = compression_cls().decompress(local_path)

        task.phase = "RESTORING"
        task.progress = 75
        db.commit()
        result = build_database_driver(target).restore(restore_file)
        task.stdout_tail = result.stdout_tail
        task.stderr_tail = result.stderr_tail
        if not result.ok:
            raise AppError("RESTORE_COMMAND_FAILED", result.stderr_tail, status_code=500)

        task.status = "SUCCESS"
        task.phase = None
        task.progress = 100
        task.duration_seconds = round(monotonic() - start, 3)
        task.ended_at = datetime.now(UTC)
        db.commit()
        add_task_event(db, task_type="restore", task_id=task.id, level="INFO", message="Restore completed")
        db.refresh(task)
        return task
    except Exception as exc:
        task.status = "FAILED"
        task.error_code = exc.code if isinstance(exc, AppError) else "RESTORE_COMMAND_FAILED"
        task.error_message = exc.message if isinstance(exc, AppError) else str(exc)
        task.duration_seconds = round(monotonic() - start, 3)
        task.ended_at = datetime.now(UTC)
        db.commit()
        add_task_event(
            db,
            task_type="restore",
            task_id=task.id,
            level="ERROR",
            phase=task.phase,
            message=task.error_message,
        )
        create_alert(
            db,
            alert_type="RESTORE_FAILED",
            severity="Critical",
            resource_type="restore_task",
            resource_id=task.id,
            title="Restore task failed",
            message=task.error_message or "Restore task failed",
            dedupe_key=f"restore:{task.backup_id}:{task.error_code}",
        )
        return task
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
