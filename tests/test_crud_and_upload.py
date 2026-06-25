from pathlib import Path

from app.core.database import SessionLocal
from app.models import Storage
from app.services.storage_service import decrypt_config
from tests.conftest import create_database_instance, create_local_storage


def test_database_and_storage_crud_do_not_expose_secrets(client, admin_headers, tmp_path):
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers)

    storage = client.get(f"/api/v1/storages/{storage_id}", headers=admin_headers)
    database = client.get(f"/api/v1/databases/{database_id}", headers=admin_headers)
    storage_test = client.post(f"/api/v1/storages/{storage_id}/test", headers=admin_headers)

    assert storage.status_code == 200
    assert storage.json()["storage_type"] == "local"
    assert "config" not in storage.json()
    assert database.status_code == 200
    assert "password" not in database.json()
    assert "password_encrypted" not in database.json()
    assert storage_test.status_code == 200
    assert storage_test.json()["ok"] is True


def test_storage_update_without_config_preserves_existing_config(client, admin_headers, tmp_path):
    root = tmp_path / "backups"
    storage_id = create_local_storage(client, admin_headers, root)

    response = client.put(
        f"/api/v1/storages/{storage_id}",
        headers=admin_headers,
        json={"name": "renamed-local"},
    )

    assert response.status_code == 200, response.text
    db = SessionLocal()
    try:
        storage = db.get(Storage, storage_id)
        assert decrypt_config(storage.config_encrypted) == {"root_path": str(root)}
    finally:
        db.close()


def test_upload_backup_verify_and_delete(client, admin_headers, tmp_path):
    storage_id = create_local_storage(client, admin_headers, tmp_path / "backups")
    database_id = create_database_instance(client, admin_headers)

    upload = client.post(
        f"/api/v1/backups/upload?database_id={database_id}&storage_id={storage_id}&compression=none",
        headers=admin_headers,
        files={"file": ("backup.sql", b"CREATE TABLE t(id int);", "application/sql")},
    )
    assert upload.status_code == 200, upload.text
    backup_id = upload.json()["backup_id"]

    backups = client.get("/api/v1/backups", headers=admin_headers)
    verify = client.post(f"/api/v1/backups/{backup_id}/verify", headers=admin_headers)
    delete = client.delete(f"/api/v1/backups/{backup_id}", headers=admin_headers)
    audit = client.get("/api/v1/audit-logs", headers=admin_headers)

    assert backups.status_code == 200
    assert backups.json()["total"] == 1
    assert verify.status_code == 200
    assert verify.json()["ok"] is True
    assert delete.status_code == 200
    assert audit.status_code == 200
    assert any(item["action"] == "backup.delete" for item in audit.json()["items"])
    assert list(Path(tmp_path / "backups").rglob("*"))  # storage directory was used
