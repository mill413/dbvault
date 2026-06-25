from pathlib import Path

from app.drivers.registry import registry
from app.scheduler.service import build_trigger
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
