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

