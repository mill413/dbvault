from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.database import SessionLocal
from app.drivers.database.base import CommandResult
from app.drivers.registry import registry
from app.models import Backup
from tests.conftest import create_database_instance, create_local_storage


class RestoreShouldNotRunDriver:
    def __init__(self, instance, password):
        self.instance = instance
        self.password = password

    def test_connection(self):
        return {"ok": True, "version": "fake", "duration_seconds": 0.001, "message": None}

    def backup(self, output_dir: Path, timeout_seconds: int = 21600):
        raise AssertionError("not used")

    def restore(self, backup_file: Path, timeout_seconds: int = 21600):
        raise AssertionError("restore should not run when checksum fails")


class SuccessfulRestoreDriver(RestoreShouldNotRunDriver):
    def restore(self, backup_file: Path, timeout_seconds: int = 21600):
        return CommandResult(True, 0, "restored", "", 0.001)


def _upload_backup(client, headers, database_id, storage_id):
    response = client.post(
        f"/api/v1/backups/upload?database_id={database_id}&storage_id={storage_id}&compression=none",
        headers=headers,
        files={"file": ("backup.sql", b"CREATE TABLE t(id int);", "application/sql")},
    )
    assert response.status_code == 200, response.text
    return response.json()["backup_id"]


def test_lifecycle_cleanup_dry_run_and_delete(client, admin_headers, tmp_path):
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers)
    backup_id = _upload_backup(client, admin_headers, database_id, storage_id)

    db = SessionLocal()
    try:
        backup = db.get(Backup, backup_id)
        backup.expires_at = datetime.now(UTC) - timedelta(days=1)
        db.commit()
    finally:
        db.close()

    dry_run = client.post("/api/v1/backups/lifecycle/run?dry_run=true", headers=admin_headers)
    cleanup = client.post("/api/v1/backups/lifecycle/run", headers=admin_headers)
    listed = client.get("/api/v1/backups", headers=admin_headers)

    assert dry_run.status_code == 200
    assert dry_run.json()["deleted_backup_ids"] == [backup_id]
    assert cleanup.status_code == 200
    assert cleanup.json()["deleted_backup_ids"] == [backup_id]
    assert listed.json()["total"] == 0


def test_original_instance_restore_requires_confirmation(client, admin_headers, tmp_path):
    registry.register_database("mysql", SuccessfulRestoreDriver)
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers, name="source")
    backup_id = _upload_backup(client, admin_headers, database_id, storage_id)

    rejected = client.post(
        "/api/v1/restore/run",
        headers=admin_headers,
        json={
            "backup_id": backup_id,
            "target_database_id": database_id,
            "restore_mode": "ORIGINAL_INSTANCE",
            "confirm_text": "wrong",
        },
    )
    accepted = client.post(
        "/api/v1/restore/run",
        headers=admin_headers,
        json={
            "backup_id": backup_id,
            "target_database_id": database_id,
            "restore_mode": "ORIGINAL_INSTANCE",
            "confirm_text": "restore source",
        },
    )

    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "CONFIRM_TEXT_INVALID"
    assert accepted.status_code == 200
    task = client.get(f"/api/v1/restore-tasks/{accepted.json()['task_id']}", headers=admin_headers)
    assert task.json()["status"] == "SUCCESS"


def test_new_instance_restore_requires_explicit_target(client, admin_headers, tmp_path):
    registry.register_database("mysql", SuccessfulRestoreDriver)
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers, name="source")
    backup_id = _upload_backup(client, admin_headers, database_id, storage_id)

    response = client.post(
        "/api/v1/restore/run",
        headers=admin_headers,
        json={"backup_id": backup_id, "restore_mode": "NEW_INSTANCE"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unknown_restore_mode_is_rejected_before_task_creation(client, admin_headers, tmp_path):
    registry.register_database("mysql", SuccessfulRestoreDriver)
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers, name="source")
    backup_id = _upload_backup(client, admin_headers, database_id, storage_id)

    response = client.post(
        "/api/v1/restore/run",
        headers=admin_headers,
        json={
            "backup_id": backup_id,
            "target_database_id": database_id,
            "restore_mode": "TYPO",
        },
    )
    tasks = client.get("/api/v1/restore-tasks", headers=admin_headers)

    assert response.status_code == 422
    assert tasks.json()["total"] == 0


def test_original_instance_restore_rejects_different_target(client, admin_headers, tmp_path):
    registry.register_database("mysql", SuccessfulRestoreDriver)
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    source_id = create_database_instance(client, admin_headers, name="source")
    target_id = create_database_instance(client, admin_headers, name="target")
    backup_id = _upload_backup(client, admin_headers, source_id, storage_id)

    response = client.post(
        "/api/v1/restore/run",
        headers=admin_headers,
        json={
            "backup_id": backup_id,
            "target_database_id": target_id,
            "restore_mode": "ORIGINAL_INSTANCE",
            "confirm_text": "restore source",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_restore_checksum_mismatch_blocks_restore_and_alerts(client, admin_headers, tmp_path):
    registry.register_database("mysql", RestoreShouldNotRunDriver)
    storage_root = tmp_path / "backups"
    storage_id = create_local_storage(client, admin_headers, storage_root)
    source_id = create_database_instance(client, admin_headers, name="source")
    target_id = create_database_instance(client, admin_headers, name="target")
    backup_id = _upload_backup(client, admin_headers, source_id, storage_id)

    backup = client.get(f"/api/v1/backups/{backup_id}", headers=admin_headers).json()
    stored_file = storage_root / backup["object_key"]
    stored_file.write_bytes(b"tampered")

    response = client.post(
        "/api/v1/restore/run",
        headers=admin_headers,
        json={"backup_id": backup_id, "target_database_id": target_id, "restore_mode": "NEW_INSTANCE"},
    )
    task = client.get(f"/api/v1/restore-tasks/{response.json()['task_id']}", headers=admin_headers)
    alerts = client.get("/api/v1/alerts?status=OPEN", headers=admin_headers)

    assert response.status_code == 200
    assert task.json()["status"] == "FAILED"
    assert task.json()["error_code"] == "CHECKSUM_MISMATCH"
    assert alerts.json()["total"] == 1
    assert alerts.json()["items"][0]["alert_type"] == "RESTORE_FAILED"
