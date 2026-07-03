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
    old_token_rejected = client.get("/api/v1/auth/me", headers=admin_headers)
    relogin = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "new-admin123456"},
    )
    new_admin_headers = {"Authorization": f"Bearer {relogin.json()['access_token']}"}
    old_refresh_rejected = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login.json()["refresh_token"]},
    )
    created = client.post(
        "/api/v1/users",
        headers=new_admin_headers,
        json={"username": "operator", "password": "operator123456", "role": "User"},
    )
    user_id = created.json()["id"]
    updated = client.put(
        f"/api/v1/users/{user_id}",
        headers=new_admin_headers,
        json={"display_name": "Ops", "role": "User"},
    )
    reset = client.post(
        f"/api/v1/users/{user_id}/reset-password",
        headers=new_admin_headers,
        json={"password": "operator654321"},
    )
    deleted = client.delete(f"/api/v1/users/{user_id}", headers=new_admin_headers)

    assert refresh.status_code == 200
    assert change.status_code == 200
    assert old_token_rejected.status_code == 401
    assert old_refresh_rejected.status_code == 401
    assert relogin.status_code == 200
    assert created.status_code == 200
    assert updated.json()["display_name"] == "Ops"
    assert updated.json()["role"] == "User"
    assert reset.status_code == 200
    assert deleted.status_code == 200


def test_user_optional_email_accepts_blank_values(client, admin_headers):
    created = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": "blank-email",
            "password": "blank12345",
            "display_name": "",
            "email": "",
            "role": "User",
        },
    )
    updated = client.put(
        f"/api/v1/users/{created.json()['id']}",
        headers=admin_headers,
        json={"email": ""},
    )

    assert created.status_code == 200
    assert created.json()["email"] is None
    assert updated.status_code == 200
    assert updated.json()["email"] is None


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


def test_run_now_respects_job_concurrency(client, admin_headers, tmp_path):
    from app.core.database import SessionLocal
    from app.models import BackupTask, Job

    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers)
    job = client.post(
        "/api/v1/jobs",
        headers=admin_headers,
        json={
            "name": "non-concurrent",
            "database_id": database_id,
            "storage_id": storage_id,
            "schedule_type": "INTERVAL",
            "interval_seconds": 3600,
            "allow_concurrent": False,
            "backup_config": {"compression": "none"},
        },
    )
    job_id = job.json()["id"]
    db = SessionLocal()
    try:
        created_by = db.get(Job, job_id).created_by
        task = BackupTask(
            database_id=database_id,
            storage_id=storage_id,
            job_id=job_id,
            status="RUNNING",
            trigger_type="JOB",
            config={},
            created_by=created_by,
        )
        db.add(task)
        db.flush()
        db.get(Job, job_id).active_backup_task_id = task.id
        db.commit()
    finally:
        db.close()

    run_now = client.post(f"/api/v1/jobs/{job_id}/run-now", headers=admin_headers)
    pending_backups = client.get("/api/v1/backups?status=PENDING", headers=admin_headers)
    backups = client.get("/api/v1/backups", headers=admin_headers)

    assert run_now.status_code == 400
    assert run_now.json()["error"]["code"] == "JOB_ALREADY_RUNNING"
    assert pending_backups.json()["total"] == 0
    assert backups.json()["total"] == 0


def test_delete_database_or_storage_rejects_enabled_jobs(client, admin_headers, tmp_path):
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers)
    job = client.post(
        "/api/v1/jobs",
        headers=admin_headers,
        json={
            "name": "keeps-resources",
            "database_id": database_id,
            "storage_id": storage_id,
            "schedule_type": "INTERVAL",
            "interval_seconds": 3600,
            "backup_config": {"compression": "none"},
        },
    )
    job_id = job.json()["id"]

    db_delete = client.delete(f"/api/v1/databases/{database_id}", headers=admin_headers)
    storage_delete = client.delete(f"/api/v1/storages/{storage_id}", headers=admin_headers)
    disabled = client.post(f"/api/v1/jobs/{job_id}/disable", headers=admin_headers)
    db_delete_after_disable = client.delete(f"/api/v1/databases/{database_id}", headers=admin_headers)
    storage_delete_after_disable = client.delete(f"/api/v1/storages/{storage_id}", headers=admin_headers)

    assert db_delete.status_code == 400
    assert db_delete.json()["error"]["code"] == "VALIDATION_ERROR"
    assert storage_delete.status_code == 400
    assert storage_delete.json()["error"]["code"] == "VALIDATION_ERROR"
    assert disabled.status_code == 200
    assert db_delete_after_disable.status_code == 200
    assert storage_delete_after_disable.status_code == 200
