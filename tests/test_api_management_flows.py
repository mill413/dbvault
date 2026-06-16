from app.drivers.database.base import BackupResult
from app.drivers.registry import registry
from tests.conftest import create_database_instance, create_local_storage


class JobBackupDriver:
    def __init__(self, instance, password):
        self.instance = instance
        self.password = password

    def test_connection(self):
        return {"ok": True, "version": "fake", "duration_seconds": 0.001, "message": None}

    def backup(self, output_dir, timeout_seconds: int = 21600):
        target = output_dir / "job.sql"
        target.write_text("SELECT 1;\n", encoding="utf-8")
        return BackupResult(
            ok=True,
            returncode=0,
            raw_file=target,
            file_format="sql",
            stdout_tail="",
            stderr_tail="",
            duration_seconds=0.001,
            database_version="fake",
        )

    def restore(self, backup_file, timeout_seconds: int = 21600):
        raise AssertionError("not used")


def test_auth_refresh_change_password_and_user_management(client, admin_headers):
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123456789"},
    )
    refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login.json()["refresh_token"]},
    )
    change = client.post(
        "/api/v1/auth/change-password",
        headers=admin_headers,
        json={"old_password": "admin123456789", "new_password": "new-admin123456"},
    )
    created = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "operator", "password": "operator123456", "role": "Operator"},
    )
    user_id = created.json()["id"]
    updated = client.put(
        f"/api/v1/users/{user_id}",
        headers=admin_headers,
        json={"display_name": "Ops", "role": "Viewer"},
    )
    reset = client.post(
        f"/api/v1/users/{user_id}/reset-password",
        headers=admin_headers,
        json={"password": "operator654321"},
    )
    deleted = client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)

    assert refresh.status_code == 200
    assert change.status_code == 200
    assert created.status_code == 200
    assert updated.json()["display_name"] == "Ops"
    assert updated.json()["role"] == "Viewer"
    assert reset.status_code == 200
    assert deleted.status_code == 200


def test_database_storage_and_job_management(client, admin_headers, tmp_path):
    registry.register_database("mysql", JobBackupDriver)
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers)

    db_list = client.get("/api/v1/databases?db_type=mysql&environment=test", headers=admin_headers)
    db_update = client.put(
        f"/api/v1/databases/{database_id}",
        headers=admin_headers,
        json={"owner": "platform", "tags": ["orders", "critical"]},
    )
    storage_update = client.put(
        f"/api/v1/storages/{storage_id}",
        headers=admin_headers,
        json={"is_default": True, "status": "ACTIVE"},
    )
    job = client.post(
        "/api/v1/jobs",
        headers=admin_headers,
        json={
            "name": "manual-job",
            "database_id": database_id,
            "storage_id": storage_id,
            "schedule_type": "INTERVAL",
            "interval_seconds": 3600,
            "backup_config": {"compression": "none"},
        },
    )
    job_id = job.json()["id"]
    job_list = client.get("/api/v1/jobs", headers=admin_headers)
    job_update = client.put(
        f"/api/v1/jobs/{job_id}",
        headers=admin_headers,
        json={"name": "renamed-job", "enabled": True},
    )
    run_now = client.post(f"/api/v1/jobs/{job_id}/run-now", headers=admin_headers)
    scheduled_backups = client.get("/api/v1/backups?source_type=SCHEDULED", headers=admin_headers)
    job_delete = client.delete(f"/api/v1/jobs/{job_id}?delete_backups=true", headers=admin_headers)
    backups_after_job_delete = client.get("/api/v1/backups", headers=admin_headers)
    db_delete = client.delete(f"/api/v1/databases/{database_id}", headers=admin_headers)
    storage_delete = client.delete(f"/api/v1/storages/{storage_id}", headers=admin_headers)

    assert db_list.status_code == 200
    assert db_list.json()["total"] == 1
    assert db_update.json()["owner"] == "platform"
    assert storage_update.json()["is_default"] is True
    assert job.status_code == 200
    assert job_list.json()["total"] == 1
    assert job_update.json()["name"] == "renamed-job"
    assert run_now.status_code == 200
    assert scheduled_backups.json()["total"] == 1
    assert scheduled_backups.json()["items"][0]["source_type"] == "SCHEDULED"
    assert job_delete.status_code == 200
    assert backups_after_job_delete.json()["total"] == 0
    assert db_delete.status_code == 200
    assert storage_delete.status_code == 200
