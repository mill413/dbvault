from pathlib import Path
from types import SimpleNamespace

from app.core.database import SessionLocal
from app.drivers.database.base import BackupResult
from app.drivers.registry import registry
from app.models import Backup, BackupTask, Job
from app.scheduler.service import build_trigger, execute_job
from tests.conftest import create_database_instance, create_local_storage


class FailingDriver:
    def __init__(self, instance, password):
        self.instance = instance
        self.password = password

    def test_connection(self):
        return {"ok": True, "version": "fake", "duration_seconds": 0.001, "message": None}

    def backup(self, output_dir: Path, timeout_seconds: int = 21600):
        raise RuntimeError("simulated backup failure")

    def restore(self, backup_file: Path, timeout_seconds: int = 21600):
        raise RuntimeError("not used")


class SuccessfulDriver:
    def __init__(self, instance, password):
        self.instance = instance
        self.password = password

    def test_connection(self):
        return {"ok": True, "version": "fake", "duration_seconds": 0.001, "message": None}

    def backup(self, output_dir: Path, timeout_seconds: int = 21600):
        raw_file = output_dir / "backup.sql"
        raw_file.write_text("select 1;\n", encoding="utf-8")
        return BackupResult(
            ok=True,
            returncode=0,
            raw_file=raw_file,
            file_format="sql",
            stdout_tail="ok",
            stderr_tail="",
            duration_seconds=0.001,
            database_version="fake",
        )

    def restore(self, backup_file: Path, timeout_seconds: int = 21600):
        raise RuntimeError("not used")


def test_failed_backup_creates_alert(client, admin_headers, tmp_path):
    registry.register_database("mysql", FailingDriver)
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers)

    response = client.post(
        "/api/v1/backups/run",
        headers=admin_headers,
        json={"database_id": database_id, "storage_id": storage_id, "compression": "none"},
    )
    task_id = response.json()["task_id"]
    task = client.get(f"/api/v1/backup-tasks/{task_id}", headers=admin_headers)
    alerts = client.get("/api/v1/alerts?status=OPEN", headers=admin_headers)

    assert task.json()["status"] == "FAILED"
    assert alerts.status_code == 200
    assert alerts.json()["total"] == 1
    alert_id = alerts.json()["items"][0]["id"]

    resolved = client.post(f"/api/v1/alerts/{alert_id}/resolve", headers=admin_headers)
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "RESOLVED"


def test_job_crud_and_trigger_building(client, admin_headers, tmp_path):
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers)

    created = client.post(
        "/api/v1/jobs",
        headers=admin_headers,
        json={
            "name": "daily",
            "database_id": database_id,
            "storage_id": storage_id,
            "schedule_type": "CRON",
            "cron_expr": "0 1 * * *",
            "retention_policy": {"keep_days": 7},
            "backup_config": {"compression": "none"},
        },
    )
    assert created.status_code == 200, created.text

    job = created.json()
    trigger = build_trigger(type("JobLike", (), job)())
    disabled = client.post(f"/api/v1/jobs/{job['id']}/disable", headers=admin_headers)

    assert trigger is not None
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False


def test_all_job_schedule_types_create_valid_triggers(client, admin_headers, tmp_path):
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers)

    cases = [
        ("cron-job", {"schedule_type": "cron", "cron_expr": "*/5 * * * *"}),
        ("interval-job", {"schedule_type": "interval", "interval_seconds": 3600}),
        ("once-job", {"schedule_type": "once", "run_at": "2099-01-01T00:00:00+08:00"}),
    ]
    for name, schedule in cases:
        response = client.post(
            "/api/v1/jobs",
            headers=admin_headers,
            json={
                "name": name,
                "database_id": database_id,
                "storage_id": storage_id,
                "backup_config": {"compression": "none"},
                **schedule,
            },
        )
        assert response.status_code == 200, response.text
        assert build_trigger(SimpleNamespace(**response.json())) is not None


def test_scheduled_job_execution_creates_job_backup_and_updates_status(client, admin_headers, tmp_path):
    registry.register_database("mysql", SuccessfulDriver)
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers)
    response = client.post(
        "/api/v1/jobs",
        headers=admin_headers,
        json={
            "name": "scheduled-success",
            "database_id": database_id,
            "storage_id": storage_id,
            "schedule_type": "interval",
            "interval_seconds": 3600,
            "backup_config": {"compression": "none"},
        },
    )
    assert response.status_code == 200, response.text
    job_id = response.json()["id"]

    execute_job(job_id)

    with SessionLocal() as db:
        job = db.get(Job, job_id)
        task = db.query(BackupTask).filter(BackupTask.job_id == job_id).one()
        backup = db.query(Backup).filter(Backup.backup_task_id == task.id).one()

        assert task.trigger_type == "JOB"
        assert task.status == "SUCCESS"
        assert backup.status == "AVAILABLE"
        assert backup.source_type == "SCHEDULED"
        assert job.last_run_at is not None
        assert job.last_status == "SUCCESS"
        assert job.active_backup_task_id is None


def test_scheduled_job_skips_when_previous_task_is_active(client, admin_headers, tmp_path):
    registry.register_database("mysql", SuccessfulDriver)
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers)
    response = client.post(
        "/api/v1/jobs",
        headers=admin_headers,
        json={
            "name": "scheduled-non-concurrent",
            "database_id": database_id,
            "storage_id": storage_id,
            "schedule_type": "interval",
            "interval_seconds": 3600,
            "backup_config": {"compression": "none"},
            "allow_concurrent": False,
        },
    )
    assert response.status_code == 200, response.text
    job_id = response.json()["id"]

    with SessionLocal() as db:
        job = db.get(Job, job_id)
        active_task = BackupTask(
            database_id=database_id,
            storage_id=storage_id,
            job_id=job_id,
            status="RUNNING",
            trigger_type="JOB",
            config={},
            created_by=job.created_by,
        )
        db.add(active_task)
        db.flush()
        job.active_backup_task_id = active_task.id
        db.commit()

    execute_job(job_id)

    with SessionLocal() as db:
        job = db.get(Job, job_id)
        task_count = db.query(BackupTask).filter(BackupTask.job_id == job_id).count()

        assert task_count == 1
        assert job.skipped_count == 1


def test_invalid_job_schedule_is_rejected_before_persisting(client, admin_headers, tmp_path):
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers)

    created = client.post(
        "/api/v1/jobs",
        headers=admin_headers,
        json={
            "name": "broken-cron",
            "database_id": database_id,
            "storage_id": storage_id,
            "schedule_type": "CRON",
        },
    )
    jobs = client.get("/api/v1/jobs", headers=admin_headers)

    assert created.status_code == 400
    assert created.json()["error"]["code"] == "VALIDATION_ERROR"
    assert jobs.json()["total"] == 0
