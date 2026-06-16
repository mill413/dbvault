from pathlib import Path

from app.drivers.database.base import BackupResult, CommandResult
from app.drivers.registry import registry
from tests.conftest import create_database_instance, create_local_storage


class FakeMySQLDriver:
    def __init__(self, instance, password):
        self.instance = instance
        self.password = password

    def test_connection(self):
        return {"ok": True, "version": "fake-mysql-8", "duration_seconds": 0.001, "message": None}

    def backup(self, output_dir: Path, timeout_seconds: int = 21600):
        target = output_dir / "orders.sql"
        target.write_text("CREATE TABLE orders(id int);\n", encoding="utf-8")
        return BackupResult(
            ok=True,
            returncode=0,
            raw_file=target,
            file_format="sql",
            stdout_tail="",
            stderr_tail="",
            duration_seconds=0.001,
            database_version="fake-mysql-8",
        )

    def restore(self, backup_file: Path, timeout_seconds: int = 21600):
        assert backup_file.exists()
        return CommandResult(
            ok=True,
            returncode=0,
            stdout_tail="restored",
            stderr_tail="",
            duration_seconds=0.001,
        )


def test_backup_run_uses_driver_and_creates_available_backup(client, admin_headers, tmp_path):
    registry.register_database("mysql", FakeMySQLDriver)
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers)

    response = client.post(
        "/api/v1/backups/run",
        headers=admin_headers,
        json={
            "database_id": database_id,
            "storage_id": storage_id,
            "compression": "none",
            "checksum": ["sha256", "md5"],
        },
    )
    assert response.status_code == 200, response.text
    task_id = response.json()["task_id"]

    task = client.get(f"/api/v1/backup-tasks/{task_id}", headers=admin_headers)
    backups = client.get("/api/v1/backups", headers=admin_headers)
    events = client.get(f"/api/v1/backup-tasks/{task_id}/events", headers=admin_headers)

    assert task.json()["status"] == "SUCCESS"
    assert backups.json()["total"] == 1
    assert backups.json()["items"][0]["status"] == "AVAILABLE"
    assert backups.json()["items"][0]["source_type"] == "MANUAL"
    assert backups.json()["items"][0]["md5"] is not None
    assert any(event["message"] == "Backup completed" for event in events.json())


def test_failed_backup_task_is_visible_in_backup_list(client, admin_headers, tmp_path):
    registry.register_database("mysql", FakeMySQLDriver)
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers)

    response = client.post(
        "/api/v1/backups/run",
        headers=admin_headers,
        json={
            "database_id": database_id,
            "storage_id": storage_id,
            "compression": "missing-driver",
            "checksum": ["sha256"],
        },
    )
    assert response.status_code == 200, response.text

    backups = client.get("/api/v1/backups?status=FAILED", headers=admin_headers)
    assert backups.status_code == 200
    assert backups.json()["total"] == 1
    assert backups.json()["items"][0]["status"] == "FAILED"
    assert backups.json()["items"][0]["source_type"] == "MANUAL"


def test_restore_run_validates_checksum_and_uses_driver(client, admin_headers, tmp_path):
    registry.register_database("mysql", FakeMySQLDriver)
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    source_id = create_database_instance(client, admin_headers, name="source")
    target_id = create_database_instance(client, admin_headers, name="target")
    upload = client.post(
        f"/api/v1/backups/upload?database_id={source_id}&storage_id={storage_id}&compression=none",
        headers=admin_headers,
        files={"file": ("backup.sql", b"CREATE TABLE t(id int);", "application/sql")},
    )
    backup_id = upload.json()["backup_id"]

    dry_run = client.post(
        "/api/v1/restore/dry-run",
        headers=admin_headers,
        json={"backup_id": backup_id, "target_database_id": target_id, "restore_mode": "NEW_INSTANCE"},
    )
    restore = client.post(
        "/api/v1/restore/run",
        headers=admin_headers,
        json={"backup_id": backup_id, "target_database_id": target_id, "restore_mode": "NEW_INSTANCE"},
    )

    assert dry_run.status_code == 200
    assert dry_run.json()["ok"] is True
    assert restore.status_code == 200, restore.text
    task_id = restore.json()["task_id"]
    task = client.get(f"/api/v1/restore-tasks/{task_id}", headers=admin_headers)
    assert task.json()["status"] == "SUCCESS"
    assert task.json()["stdout_tail"] == "restored"
