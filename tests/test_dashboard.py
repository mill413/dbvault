from datetime import UTC, date, datetime, timedelta

from app.core.database import SessionLocal
from app.models import BackupTask
from tests.conftest import create_database_instance, create_local_storage


def test_dashboard_summary(client, admin_headers, tmp_path):
    create_local_storage(client, admin_headers, tmp_path / "backups")
    create_database_instance(client, admin_headers)

    summary = client.get("/api/v1/dashboard/summary", headers=admin_headers)
    trends = client.get("/api/v1/dashboard/backup-trends", headers=admin_headers)
    usage = client.get("/api/v1/dashboard/storage-usage", headers=admin_headers)

    assert summary.status_code == 200
    assert summary.json()["database_count"] == 1
    assert summary.json()["storage_count"] == 1
    assert trends.status_code == 200
    assert trends.json() == []
    assert usage.status_code == 200
    assert usage.json() == []


def test_backup_trends_groups_existing_tasks(client, admin_headers, tmp_path):
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers)
    today = date.today().isoformat()

    with SessionLocal() as db:
        db.add_all(
            [
                BackupTask(
                    database_id=database_id,
                    storage_id=storage_id,
                    status="SUCCESS",
                    trigger_type="MANUAL",
                    created_by=1,
                    created_at=datetime.now(UTC),
                ),
                BackupTask(
                    database_id=database_id,
                    storage_id=storage_id,
                    status="FAILED",
                    trigger_type="MANUAL",
                    created_by=1,
                    created_at=datetime.now(UTC) - timedelta(hours=1),
                ),
            ]
        )
        db.commit()

    response = client.get("/api/v1/dashboard/backup-trends?days=3", headers=admin_headers)

    assert response.status_code == 200
    trend = next(item for item in response.json() if item["date"] == today)
    assert trend["success_count"] == 1
    assert trend["failed_count"] == 1
