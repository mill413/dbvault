import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.ownership import ensure_owner
from app.drivers.registry import registry
from app.models import Backup, BackupTask, DatabaseInstance, Storage, User
from app.services.alert_service import create_alert
from app.services.audit_service import add_task_event
from app.services.database_service import build_database_driver
from app.services.lifecycle_service import calculate_expires_at
from app.services.storage_service import build_storage_driver, get_default_storage, get_storage_usage
from app.utils.checksum import file_checksum
from app.utils.paths import build_backup_object_key


def _check_storage_capacity(db: Session, storage: Storage, additional_bytes: int) -> None:
    if not storage.capacity_limit_bytes:
        return
    used = get_storage_usage(db, storage)
    if used + additional_bytes > storage.capacity_limit_bytes:
        usage_pct = round((used / storage.capacity_limit_bytes) * 100, 1)
        create_alert(
            db,
            alert_type="CAPACITY_WARNING",
            severity="High",
            resource_type="storage",
            resource_id=storage.id,
            title="Storage capacity limit exceeded",
            message=(
                f"Storage '{storage.name}' usage ({usage_pct}%) plus new backup "
                f"({additional_bytes} bytes) exceeds capacity limit "
                f"({storage.capacity_limit_bytes} bytes)"
            ),
            dedupe_key=f"capacity:{storage.id}",
        )


def create_backup_task(db: Session, payload, user: User, trigger_type: str = "MANUAL") -> BackupTask:
    storage = db.get(Storage, payload.storage_id) if payload.storage_id else get_default_storage(db, user=user)
    if not storage or storage.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Storage not found", status_code=404)
    ensure_owner(storage, user, "Storage not found")
    instance = db.get(DatabaseInstance, payload.database_id)
    if not instance or instance.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Database instance not found", status_code=404)
    ensure_owner(instance, user, "Database instance not found")
    task = BackupTask(
        database_id=instance.id,
        storage_id=storage.id,
        status="PENDING",
        trigger_type=trigger_type,
        config=payload.model_dump(),
        created_by=user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    backup = Backup(
        database_id=instance.id,
        storage_id=storage.id,
        backup_task_id=task.id,
        backup_type="LOGICAL",
        status=task.status,
        object_key="",
        filename=f"backup-task-{task.id}",
        file_format="pending",
        size_bytes=0,
        compressed=payload.compression != "none",
        compression=payload.compression if payload.compression != "none" else None,
        sha256="",
        expires_at=calculate_expires_at(payload.retention),
        created_by=user.id,
        extra_metadata={"source": "driver"},
    )
    db.add(backup)
    db.commit()
    add_task_event(db, task_type="backup", task_id=task.id, level="INFO", message="Task created")
    return task


def run_backup_task(db: Session, task_id: int) -> BackupTask:
    task = db.get(BackupTask, task_id)
    if not task:
        raise AppError("RESOURCE_NOT_FOUND", "Backup task not found", status_code=404)
    settings = get_settings()
    start = monotonic()
    task.status = "RUNNING"
    task.phase = "DUMPING"
    task.progress = 5
    task.started_at = datetime.now(UTC)
    backup = db.query(Backup).filter(Backup.backup_task_id == task.id).first()
    if backup:
        backup.status = "RUNNING"
        backup.started_at = task.started_at
    db.commit()
    add_task_event(db, task_type="backup", task_id=task.id, level="INFO", phase="DUMPING", message="Dump started")

    tmp_root = settings.backup_tmp_dir
    tmp_root.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix=f"backup-{task.id}-", dir=tmp_root))
    try:
        instance = db.get(DatabaseInstance, task.database_id)
        storage = db.get(Storage, task.storage_id)
        if not instance or not storage:
            raise AppError("RESOURCE_NOT_FOUND", "Task resource not found", status_code=404)

        db_driver = build_database_driver(instance)
        backup_result = db_driver.backup(work_dir)
        task.stdout_tail = backup_result.stdout_tail
        task.stderr_tail = backup_result.stderr_tail
        db.commit()
        if not backup_result.ok:
            message = backup_result.stderr_tail or f"Backup command failed with {backup_result.returncode}"
            raise AppError("BACKUP_COMMAND_FAILED", message, status_code=500)
        if not backup_result.raw_file.exists():
            raise AppError("BACKUP_COMMAND_FAILED", "Backup command produced no output file", status_code=500)

        compression_name = task.config.get("compression", "zstd")
        task.phase = "COMPRESSING"
        task.progress = 35
        db.commit()
        add_task_event(
            db,
            task_type="backup",
            task_id=task.id,
            level="INFO",
            phase="COMPRESSING",
            message=f"Compression started: {compression_name}",
        )
        try:
            compression_cls = registry.get_compression(compression_name)
        except KeyError as exc:
            raise AppError("COMPRESSION_DRIVER_NOT_FOUND", str(exc), status_code=400) from exc
        compressed_file = compression_cls().compress(backup_result.raw_file)
        compressed = compression_name != "none"

        task.phase = "CHECKSUMING"
        task.progress = 55
        db.commit()
        sha256 = file_checksum(compressed_file, "sha256")
        md5 = file_checksum(compressed_file, "md5") if "md5" in task.config.get("checksum", []) else None

        backup = db.query(Backup).filter(Backup.backup_task_id == task.id).first()
        if not backup:
            backup = Backup(
                database_id=instance.id,
                storage_id=storage.id,
                backup_task_id=task.id,
                backup_type="LOGICAL",
                status="UPLOADING",
                object_key="pending",
                filename=compressed_file.name,
                file_format=backup_result.file_format,
                size_bytes=compressed_file.stat().st_size,
                compressed=compressed,
                compression=compression_name if compressed else None,
                md5=md5,
                sha256=sha256,
                database_version=backup_result.database_version,
                started_at=task.started_at,
                expires_at=calculate_expires_at(task.config.get("retention", {})),
                created_by=task.created_by,
                extra_metadata={"source": "driver"},
            )
            db.add(backup)
            db.commit()
            db.refresh(backup)
        else:
            backup.status = "UPLOADING"
            backup.object_key = "pending"
            backup.filename = compressed_file.name
            backup.file_format = backup_result.file_format
            backup.size_bytes = compressed_file.stat().st_size
            backup.compressed = compressed
            backup.compression = compression_name if compressed else None
            backup.md5 = md5
            backup.sha256 = sha256
            backup.database_version = backup_result.database_version
            backup.started_at = task.started_at
            backup.expires_at = calculate_expires_at(task.config.get("retention", {}))
            db.commit()
            db.refresh(backup)

        extension = compressed_file.name.split(".", 1)[1] if "." in compressed_file.name else compressed_file.suffix
        object_key = build_backup_object_key(
            instance.db_type,
            instance.environment,
            instance.name,
            backup.id,
            datetime.now(UTC),
            extension,
        )
        task.phase = "UPLOADING"
        task.progress = 75
        db.commit()
        _check_storage_capacity(db, storage, compressed_file.stat().st_size)
        storage_driver = build_storage_driver(storage)
        storage_driver.upload(
            compressed_file,
            object_key,
            {"sha256": sha256, "database_id": instance.id, "backup_id": backup.id},
        )
        backup.object_key = object_key
        backup.status = "AVAILABLE"
        backup.completed_at = datetime.now(UTC)
        task.status = "SUCCESS"
        task.phase = None
        task.progress = 100
        task.size_bytes = backup.size_bytes
        task.duration_seconds = round(monotonic() - start, 3)
        task.ended_at = datetime.now(UTC)
        db.commit()
        add_task_event(db, task_type="backup", task_id=task.id, level="INFO", message="Backup completed")
        db.refresh(task)
        return task
    except Exception as exc:
        task.status = "FAILED"
        task.error_code = exc.code if isinstance(exc, AppError) else "BACKUP_COMMAND_FAILED"
        task.error_message = exc.message if isinstance(exc, AppError) else str(exc)
        task.ended_at = datetime.now(UTC)
        task.duration_seconds = round(monotonic() - start, 3)
        backup = db.query(Backup).filter(Backup.backup_task_id == task.id).first()
        if backup:
            backup.status = "FAILED"
            backup.completed_at = task.ended_at
        db.commit()
        add_task_event(
            db,
            task_type="backup",
            task_id=task.id,
            level="ERROR",
            phase=task.phase,
            message=task.error_message,
        )
        create_alert(
            db,
            alert_type="BACKUP_FAILED",
            severity="Critical",
            resource_type="backup_task",
            resource_id=task.id,
            title="Backup task failed",
            message=task.error_message or "Backup task failed",
            dedupe_key=f"backup:{task.database_id}:{task.error_code}",
        )
        return task
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def upload_backup_file(
    db: Session,
    *,
    database_id: int,
    storage_id: int | None,
    file: UploadFile,
    compression: str,
    user: User,
) -> Backup:
    settings = get_settings()
    instance = db.get(DatabaseInstance, database_id)
    if not instance or instance.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Database instance not found", status_code=404)
    storage = db.get(Storage, storage_id) if storage_id else get_default_storage(db, user=user)
    if not storage or storage.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Storage not found", status_code=404)
    ensure_owner(storage, user, "Storage not found")
    ensure_owner(instance, user, "Database instance not found")
    settings.backup_tmp_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=settings.backup_tmp_dir) as tmp:
        shutil.copyfileobj(file.file, tmp)
        local_path = Path(tmp.name)
    try:
        sha256 = file_checksum(local_path, "sha256")
        md5 = file_checksum(local_path, "md5")
        backup = Backup(
            database_id=instance.id,
            storage_id=storage.id,
            backup_type="UPLOAD",
            status="UPLOADING",
            object_key="pending",
            filename=file.filename or local_path.name,
            file_format=(file.filename or "backup").split(".")[-1],
            size_bytes=local_path.stat().st_size,
            compressed=compression != "none",
            compression=compression if compression != "none" else None,
            md5=md5,
            sha256=sha256,
            completed_at=datetime.now(UTC),
            created_by=user.id,
            extra_metadata={"source": "upload"},
        )
        db.add(backup)
        db.commit()
        db.refresh(backup)
        extension = backup.filename.split(".", 1)[1] if "." in backup.filename else backup.file_format
        object_key = build_backup_object_key(
            instance.db_type,
            instance.environment,
            instance.name,
            backup.id,
            datetime.now(UTC),
            extension,
        )
        _check_storage_capacity(db, storage, local_path.stat().st_size)
        build_storage_driver(storage).upload(local_path, object_key, {"sha256": sha256})
        backup.object_key = object_key
        backup.status = "AVAILABLE"
        db.commit()
        db.refresh(backup)
        return backup
    finally:
        local_path.unlink(missing_ok=True)


def verify_backup(db: Session, backup: Backup) -> dict:
    storage = db.get(Storage, backup.storage_id)
    if not storage:
        raise AppError("RESOURCE_NOT_FOUND", "Storage not found", status_code=404)
    settings = get_settings()
    settings.backup_tmp_dir.mkdir(parents=True, exist_ok=True)
    local_path = settings.backup_tmp_dir / f"verify-{backup.id}-{backup.filename}"
    try:
        build_storage_driver(storage).download(backup.object_key, local_path)
        actual = file_checksum(local_path, "sha256")
        ok = actual == backup.sha256
        if not ok:
            backup.status = "VERIFY_FAILED"
            db.commit()
        return {"ok": ok, "expected_sha256": backup.sha256, "actual_sha256": actual}
    finally:
        local_path.unlink(missing_ok=True)


def delete_backup_record(db: Session, backup: Backup) -> Backup:
    backup.status = "DELETING"
    db.commit()
    if backup.object_key and backup.object_key != "pending":
        build_storage_driver(backup.storage).delete(backup.object_key)
    backup.status = "DELETED"
    backup.deleted_at = datetime.now(UTC)
    db.commit()
    db.refresh(backup)
    return backup
