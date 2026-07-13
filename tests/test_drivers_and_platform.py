from pathlib import Path

import pytest
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.encryption import get_fernet
from app.core.logging import mask_secret
from app.drivers.compression.gzip import GzipCompressionDriver
from app.drivers.compression.zstd import ZstdCompressionDriver
from app.drivers.database.command import run_command
from app.drivers.storage.local import LocalStorageDriver
from app.drivers.storage.s3 import S3StorageDriver


def test_compression_drivers_round_trip(tmp_path):
    source = tmp_path / "backup.sql"
    source.write_text("CREATE TABLE t(id int);\n", encoding="utf-8")

    zstd_file = ZstdCompressionDriver().compress(source)
    zstd_out = ZstdCompressionDriver().decompress(zstd_file, tmp_path / "zstd.out")
    gzip_file = GzipCompressionDriver().compress(source)
    gzip_out = GzipCompressionDriver().decompress(gzip_file, tmp_path / "gzip.out")

    assert zstd_out.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    assert gzip_out.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


def test_run_command_handles_missing_binary_and_masks_secrets():
    result = run_command(["definitely-not-a-real-db-backup-command"])

    assert result.ok is False
    assert result.returncode == 127
    assert "Command not found" in result.stderr_tail
    assert mask_secret("--password=secret PGPASSWORD=secret") == "--password=*** PGPASSWORD=***"


def test_s3_storage_driver_calls_boto3(monkeypatch, tmp_path):
    calls = []

    class FakeClient:
        def upload_file(self, filename, bucket, key, ExtraArgs=None):
            calls.append(("upload", Path(filename).name, bucket, key, ExtraArgs))

        def download_file(self, bucket, key, filename):
            calls.append(("download", bucket, key, Path(filename).name))
            Path(filename).write_text("downloaded", encoding="utf-8")

        def head_object(self, Bucket, Key):
            calls.append(("head", Bucket, Key))
            return {"ContentLength": 10, "Metadata": {"sha256": "abc"}}

        def delete_object(self, Bucket, Key):
            calls.append(("delete", Bucket, Key))

        def head_bucket(self, Bucket):
            calls.append(("head_bucket", Bucket))

    monkeypatch.setattr("app.drivers.storage.s3.boto3.client", lambda *args, **kwargs: FakeClient())
    driver = S3StorageDriver(
        {
            "bucket": "dbvault",
            "endpoint_url": "http://minio:9000",
            "access_key": "access",
            "secret_key": "secret",
            "use_ssl": False,
        }
    )
    source = tmp_path / "backup.sql"
    source.write_text("sql", encoding="utf-8")
    target = tmp_path / "download.sql"

    upload = driver.upload(source, "mysql/backup.sql", {"sha256": "abc"})
    driver.download("mysql/backup.sql", target)
    assert driver.exists("mysql/backup.sql") is True
    stat = driver.stat("mysql/backup.sql")
    delete = driver.delete("mysql/backup.sql")
    test = driver.test()

    assert upload["size_bytes"] == 3
    assert target.read_text(encoding="utf-8") == "downloaded"
    assert stat["metadata"]["sha256"] == "abc"
    assert delete["deleted"] is True
    assert test["ok"] is True
    assert calls[0][0] == "upload"


def test_local_storage_rejects_sibling_prefix_escape(tmp_path):
    root = tmp_path / "dbvault-root"
    source = tmp_path / "backup.sql"
    source.write_text("sql", encoding="utf-8")
    driver = LocalStorageDriver({"root_path": str(root)})

    with pytest.raises(ValueError, match="escapes storage root"):
        driver.upload(source, "../dbvault-root-evil/backup.sql")


def test_local_storage_preserves_metadata_contract(tmp_path):
    root = tmp_path / "backups"
    source = tmp_path / "backup.sql"
    source.write_text("sql", encoding="utf-8")
    driver = LocalStorageDriver({"root_path": str(root)})

    upload = driver.upload(source, "mysql/backup.sql", {"sha256": "abc"})
    stat = driver.stat("mysql/backup.sql")
    delete = driver.delete("mysql/backup.sql")

    assert upload["metadata"]["sha256"] == "abc"
    assert stat["metadata"]["sha256"] == "abc"
    assert delete["deleted"] is True
    assert not list(root.rglob("*.meta.json"))


def test_s3_exists_only_treats_not_found_as_false(monkeypatch):
    class FakeClient:
        def __init__(self, code):
            self.code = code

        def head_object(self, Bucket, Key):
            raise ClientError({"Error": {"Code": self.code}}, "HeadObject")

    driver = S3StorageDriver(
        {
            "bucket": "dbvault",
            "endpoint_url": "http://minio:9000",
            "access_key": "access",
            "secret_key": "secret",
            "use_ssl": False,
        }
    )
    monkeypatch.setattr("app.drivers.storage.s3.boto3.client", lambda *args, **kwargs: FakeClient("404"))
    assert driver.exists("missing.sql") is False

    monkeypatch.setattr("app.drivers.storage.s3.boto3.client", lambda *args, **kwargs: FakeClient("403"))
    with pytest.raises(ClientError):
        driver.exists("forbidden.sql")


def test_encryption_key_is_required_in_prod(monkeypatch):
    try:
        get_settings.cache_clear()
        monkeypatch.setenv("DBVAULT_ENV", "prod")
        monkeypatch.delenv("DBVAULT_ENCRYPTION_KEY", raising=False)
        monkeypatch.setenv("DBVAULT_JWT_SECRET", "prod-secret-without-fernet-key")

        with pytest.raises(RuntimeError, match="DBVAULT_ENCRYPTION_KEY is required"):
            get_fernet()
    finally:
        get_settings.cache_clear()


def test_login_failure_is_audited_and_openapi_available(client):
    failed = client.post("/api/v1/auth/login", json={"username": "admin", "password": "bad-password"})
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123456789"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    audit = client.get("/api/v1/audit-logs", headers=headers)
    openapi = client.get("/openapi.json")

    assert failed.status_code == 401
    assert any(item["result"] == "failed" and item["action"] == "auth.login" for item in audit.json()["items"])
    assert openapi.status_code == 200
    assert "/api/v1/backups/run" in openapi.json()["paths"]
