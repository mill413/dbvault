import os
import shutil
import subprocess
import time

import boto3
import pytest
from botocore.exceptions import ClientError

from tests.conftest import create_local_storage

RUN_INTEGRATION = os.getenv("DBVAULT_RUN_INTEGRATION") == "1"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not RUN_INTEGRATION, reason="set DBVAULT_RUN_INTEGRATION=1 to run Docker integration tests"),
]

MYSQL_HOST = os.getenv("DBVAULT_IT_MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("DBVAULT_IT_MYSQL_PORT", "13306")
MYSQL_ROOT_PASSWORD = os.getenv("DBVAULT_IT_MYSQL_ROOT_PASSWORD", "root-password")
MYSQL_USER = os.getenv("DBVAULT_IT_MYSQL_USER", "backup")
MYSQL_PASSWORD = os.getenv("DBVAULT_IT_MYSQL_PASSWORD", "backup-password")

POSTGRES_HOST = os.getenv("DBVAULT_IT_POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = os.getenv("DBVAULT_IT_POSTGRES_PORT", "15433")
POSTGRES_USER = os.getenv("DBVAULT_IT_POSTGRES_USER", "backup")
POSTGRES_PASSWORD = os.getenv("DBVAULT_IT_POSTGRES_PASSWORD", "backup-password")

MINIO_ENDPOINT = os.getenv("DBVAULT_IT_MINIO_ENDPOINT", "http://127.0.0.1:19000")
MINIO_ACCESS_KEY = os.getenv("DBVAULT_IT_MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("DBVAULT_IT_MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("DBVAULT_IT_MINIO_BUCKET", "dbvault-integration")


def _require_binary(name: str) -> None:
    if shutil.which(name) is None:
        pytest.skip(f"{name} is required for integration tests")


def _run(args: list[str], *, env: dict[str, str] | None = None, timeout: int = 30) -> subprocess.CompletedProcess:
    result = subprocess.run(
        args,
        env={**os.environ, **(env or {})},
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"command failed: {' '.join(args)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def _retry(callback, *, timeout_seconds: int = 90, interval_seconds: float = 2.0):
    deadline = time.monotonic() + timeout_seconds
    last_error = None
    while time.monotonic() < deadline:
        try:
            return callback()
        except Exception as exc:  # noqa: BLE001 - surface the last readiness failure after timeout
            last_error = exc
            time.sleep(interval_seconds)
    raise AssertionError(f"integration dependency did not become ready: {last_error}") from last_error


def _mysql_root(sql: str) -> str:
    return _run(
        [
            "mysql",
            "--protocol=tcp",
            "-h",
            MYSQL_HOST,
            "-P",
            MYSQL_PORT,
            "-u",
            "root",
            "-e",
            sql,
        ],
        env={"MYSQL_PWD": MYSQL_ROOT_PASSWORD},
    ).stdout


def _mysql_user(database: str, sql: str) -> str:
    return _run(
        [
            "mysql",
            "--protocol=tcp",
            "-h",
            MYSQL_HOST,
            "-P",
            MYSQL_PORT,
            "-u",
            MYSQL_USER,
            "--batch",
            "--skip-column-names",
            database,
            "-e",
            sql,
        ],
        env={"MYSQL_PWD": MYSQL_PASSWORD},
    ).stdout.strip()


def _prepare_mysql() -> None:
    _require_binary("mysql")
    _require_binary("mysqldump")
    _retry(lambda: _mysql_root("SELECT 1;"))
    _mysql_root(
        """
        CREATE DATABASE IF NOT EXISTS orders;
        CREATE DATABASE IF NOT EXISTS orders_restore;
        GRANT ALL PRIVILEGES ON orders.* TO 'backup'@'%';
        GRANT ALL PRIVILEGES ON orders_restore.* TO 'backup'@'%';
        FLUSH PRIVILEGES;
        DROP TABLE IF EXISTS orders.dbvault_items;
        DROP TABLE IF EXISTS orders_restore.dbvault_items;
        CREATE TABLE orders.dbvault_items (id INT PRIMARY KEY, note VARCHAR(64) NOT NULL);
        INSERT INTO orders.dbvault_items (id, note) VALUES (1, 'mysql-source');
        """
    )


def _psql(database: str, sql: str) -> str:
    return _run(
        [
            "psql",
            "--host",
            POSTGRES_HOST,
            "--port",
            POSTGRES_PORT,
            "--username",
            POSTGRES_USER,
            "--dbname",
            database,
            "--tuples-only",
            "--no-align",
            "--command",
            sql,
        ],
        env={"PGPASSWORD": POSTGRES_PASSWORD},
    ).stdout.strip()


def _prepare_postgres() -> None:
    _require_binary("psql")
    _require_binary("pg_dump")
    _retry(lambda: _psql("postgres", "SELECT 1;"))
    _psql(
        "postgres",
        """
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname IN ('reports', 'reports_restore') AND pid <> pg_backend_pid();
        """,
    )
    for database in ("reports", "reports_restore"):
        _psql("postgres", f"DROP DATABASE IF EXISTS {database};")
        _psql("postgres", f"CREATE DATABASE {database};")
    _psql(
        "reports",
        """
        CREATE TABLE dbvault_items (id INT PRIMARY KEY, note TEXT NOT NULL);
        INSERT INTO dbvault_items (id, note) VALUES (1, 'postgres-source');
        """,
    )


def _ensure_minio_bucket() -> None:
    def connect_and_create_bucket():
        client = boto3.client(
            "s3",
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            region_name="us-east-1",
        )
        try:
            client.head_bucket(Bucket=MINIO_BUCKET)
        except ClientError:
            client.create_bucket(Bucket=MINIO_BUCKET)
        return client

    _retry(connect_and_create_bucket)


def _create_database(client, headers, payload: dict) -> int:
    response = client.post("/api/v1/databases", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _database_payload(db_type: str, port: int, name: str, database_name: str) -> dict:
    return {
        "name": name,
        "db_type": db_type,
        "host": "127.0.0.1",
        "port": port,
        "username": MYSQL_USER if db_type == "mysql" else POSTGRES_USER,
        "password": MYSQL_PASSWORD if db_type == "mysql" else POSTGRES_PASSWORD,
        "database_name": database_name,
        "environment": "integration",
        "tags": ["integration"],
    }


def _assert_connection_ok(client, headers, database_id: int) -> None:
    response = client.post(f"/api/v1/databases/{database_id}/test", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["ok"] is True


def _run_backup(client, headers, database_id: int, storage_id: int) -> int:
    response = client.post(
        "/api/v1/backups/run",
        headers=headers,
        json={
            "database_id": database_id,
            "storage_id": storage_id,
            "compression": "none",
            "checksum": ["sha256"],
        },
    )
    assert response.status_code == 200, response.text
    task = client.get(f"/api/v1/backup-tasks/{response.json()['task_id']}", headers=headers)
    assert task.status_code == 200, task.text
    assert task.json()["status"] == "SUCCESS"
    backups = client.get("/api/v1/backups", headers=headers)
    assert backups.status_code == 200, backups.text
    assert backups.json()["total"] == 1
    return backups.json()["items"][0]["id"]


def _restore_backup(client, headers, backup_id: int, target_database_id: int) -> None:
    response = client.post(
        "/api/v1/restore/run",
        headers=headers,
        json={
            "backup_id": backup_id,
            "target_database_id": target_database_id,
            "restore_mode": "NEW_INSTANCE",
        },
    )
    assert response.status_code == 200, response.text
    task = client.get(f"/api/v1/restore-tasks/{response.json()['task_id']}", headers=headers)
    assert task.status_code == 200, task.text
    payload = task.json()
    assert payload["status"] == "SUCCESS", (
        f"{payload['error_code']}: {payload['error_message']} "
        f"stdout={payload['stdout_tail']} stderr={payload['stderr_tail']}"
    )


def test_mysql_backup_restore_round_trip_with_real_server(client, admin_headers, tmp_path):
    _prepare_mysql()
    storage_id = create_local_storage(client, admin_headers, tmp_path / "mysql-backups")
    source_id = _create_database(
        client,
        admin_headers,
        _database_payload("mysql", int(MYSQL_PORT), "mysql-source", "orders"),
    )
    target_id = _create_database(
        client,
        admin_headers,
        _database_payload("mysql", int(MYSQL_PORT), "mysql-target", "orders_restore"),
    )
    _assert_connection_ok(client, admin_headers, source_id)
    _assert_connection_ok(client, admin_headers, target_id)

    backup_id = _run_backup(client, admin_headers, source_id, storage_id)
    verify = client.post(f"/api/v1/backups/{backup_id}/verify", headers=admin_headers)
    _restore_backup(client, admin_headers, backup_id, target_id)

    assert verify.status_code == 200, verify.text
    assert verify.json()["ok"] is True
    assert _mysql_user("orders_restore", "SELECT note FROM dbvault_items WHERE id = 1;") == "mysql-source"


def test_postgresql_backup_restore_round_trip_with_minio(client, admin_headers):
    _prepare_postgres()
    _ensure_minio_bucket()
    storage = client.post(
        "/api/v1/storages",
        headers=admin_headers,
        json={
            "name": "minio-integration",
            "storage_type": "minio",
            "config": {
                "endpoint_url": MINIO_ENDPOINT,
                "bucket": MINIO_BUCKET,
                "access_key": MINIO_ACCESS_KEY,
                "secret_key": MINIO_SECRET_KEY,
                "use_ssl": False,
                "path_style": True,
            },
            "is_default": True,
        },
    )
    assert storage.status_code == 200, storage.text
    storage_id = storage.json()["id"]
    storage_test = client.post(f"/api/v1/storages/{storage_id}/test", headers=admin_headers)
    assert storage_test.status_code == 200, storage_test.text
    assert storage_test.json()["ok"] is True

    source_id = _create_database(
        client,
        admin_headers,
        _database_payload("postgresql", int(POSTGRES_PORT), "postgres-source", "reports"),
    )
    target_id = _create_database(
        client,
        admin_headers,
        _database_payload("postgresql", int(POSTGRES_PORT), "postgres-target", "reports_restore"),
    )
    _assert_connection_ok(client, admin_headers, source_id)
    _assert_connection_ok(client, admin_headers, target_id)

    backup_id = _run_backup(client, admin_headers, source_id, storage_id)
    verify = client.post(f"/api/v1/backups/{backup_id}/verify", headers=admin_headers)
    _restore_backup(client, admin_headers, backup_id, target_id)

    assert verify.status_code == 200, verify.text
    assert verify.json()["ok"] is True
    assert _psql("reports_restore", "SELECT note FROM dbvault_items WHERE id = 1;") == "postgres-source"
