import os
import shutil
import tempfile
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient

from alembic import command

TEST_ROOT = Path(tempfile.mkdtemp(prefix="dbvault-tests-"))
os.environ["DBVAULT_DATABASE_URL"] = f"sqlite:///{TEST_ROOT / 'test.db'}"
os.environ["DBVAULT_JWT_SECRET"] = "test-secret"
os.environ["DBVAULT_BACKUP_TMP_DIR"] = str(TEST_ROOT / "tmp")
os.environ["DBVAULT_LOCAL_STORAGE_ROOT"] = str(TEST_ROOT / "backups")
os.environ["DBVAULT_KUBECONFIG_DIR"] = str(TEST_ROOT / "kubeconfigs")
os.environ["DBVAULT_RUN_BACKGROUND_TASKS_INLINE"] = "true"
os.environ["DBVAULT_SCHEDULER_ENABLED"] = "false"
os.environ["DBVAULT_INITIAL_ADMIN_PASSWORD"] = "admin123456789"

from app.drivers.bootstrap import register_builtin_drivers  # noqa: E402
from app.main import app  # noqa: E402


def _alembic_config() -> Config:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", os.environ["DBVAULT_DATABASE_URL"])
    return config


@pytest.fixture(autouse=True)
def reset_database():
    register_builtin_drivers()
    shutil.rmtree(TEST_ROOT / "kubeconfigs", ignore_errors=True)
    shutil.rmtree(TEST_ROOT / "backups", ignore_errors=True)
    shutil.rmtree(TEST_ROOT / "case-backups", ignore_errors=True)
    command.downgrade(_alembic_config(), "base")
    command.upgrade(_alembic_config(), "head")
    yield
    command.downgrade(_alembic_config(), "base")


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_headers(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123456789"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_local_storage(client, headers, root: Path | None = None) -> int:
    root = root or (TEST_ROOT / "case-backups")
    response = client.post(
        "/api/v1/storages",
        headers=headers,
        json={
            "name": "local",
            "storage_type": "local",
            "config": {"root_path": str(root)},
            "is_default": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def create_database_instance(client, headers, *, name: str = "orders") -> int:
    response = client.post(
        "/api/v1/databases",
        headers=headers,
        json={
            "name": name,
            "db_type": "mysql",
            "host": "127.0.0.1",
            "port": 3306,
            "username": "backup",
            "password": "database-password",
            "database_name": "orders",
            "environment": "test",
            "tags": ["orders"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]
