from pathlib import Path

from app.core.encryption import encrypt_secret
from app.drivers.database.mysql import MySQLDriver
from app.drivers.database.postgresql import PostgreSQLDriver
from app.models import DatabaseInstance


def test_mysql_driver_uses_argument_array_and_env_password(monkeypatch, tmp_path):
    calls = []

    def fake_run(args, *, env=None, input_file=None, output_file=None, timeout_seconds=21600):
        calls.append({"args": args, "env": env, "output_file": output_file})
        if output_file:
            output_file.write(b"CREATE TABLE t(id int);")
        from app.drivers.database.base import CommandResult

        return CommandResult(True, 0, "8.4", "", 0.001)

    monkeypatch.setattr("app.drivers.database.mysql.run_command", fake_run)
    instance = DatabaseInstance(
        name="mysql",
        db_type="mysql",
        host="127.0.0.1",
        port=3306,
        username="backup",
        password_encrypted=encrypt_secret("secret"),
        database_name="orders",
        environment="test",
        tags=[],
    )
    driver = MySQLDriver(instance, "secret")

    test_result = driver.test_connection()
    backup_result = driver.backup(tmp_path)

    assert test_result["ok"] is True
    assert calls[0]["args"][0] == "mysql"
    assert calls[0]["env"]["MYSQL_PWD"] == "secret"
    assert calls[1]["args"][0] == "mysqldump"
    assert "--single-transaction" in calls[1]["args"]
    assert "--no-tablespaces" in calls[1]["args"]
    assert "--databases" not in calls[1]["args"]
    assert calls[1]["args"][-1] == "orders"
    assert backup_result.raw_file.read_text(encoding="utf-8") == "CREATE TABLE t(id int);"


def test_mysql_driver_sanitizes_backup_output_filename(monkeypatch, tmp_path):
    def fake_run(args, *, env=None, input_file=None, output_file=None, timeout_seconds=21600):
        if output_file:
            output_file.write(b"CREATE TABLE t(id int);")
        from app.drivers.database.base import CommandResult

        return CommandResult(True, 0, "8.4", "", 0.001)

    monkeypatch.setattr("app.drivers.database.mysql.run_command", fake_run)
    instance = DatabaseInstance(
        name="mysql",
        db_type="mysql",
        host="127.0.0.1",
        port=3306,
        username="backup",
        password_encrypted=encrypt_secret("secret"),
        database_name="../orders",
        environment="test",
        tags=[],
    )

    backup_result = MySQLDriver(instance, "secret").backup(tmp_path)

    assert backup_result.raw_file.parent.resolve() == tmp_path.resolve()
    assert backup_result.raw_file.name == "orders.sql"


def test_postgresql_driver_uses_pgpassword_and_restore_file(monkeypatch, tmp_path):
    calls = []

    def fake_run(args, *, env=None, input_file=None, output_file=None, timeout_seconds=21600):
        calls.append({"args": args, "env": env})
        if "--file" in args:
            restore_file = Path(args[args.index("--file") + 1])
            assert "transaction_timeout" not in restore_file.read_text(encoding="utf-8")
        from app.drivers.database.base import CommandResult

        return CommandResult(True, 0, "PostgreSQL 16", "", 0.001)

    monkeypatch.setattr("app.drivers.database.postgresql.run_command", fake_run)
    instance = DatabaseInstance(
        name="postgres",
        db_type="postgresql",
        host="127.0.0.1",
        port=5432,
        username="backup",
        password_encrypted=encrypt_secret("secret"),
        database_name="reports",
        environment="test",
        tags=[],
    )
    driver = PostgreSQLDriver(instance, "secret")
    backup_file = tmp_path / "backup.sql"
    backup_file.write_text("SET transaction_timeout = 0;\nCREATE TABLE t(id int);\n", encoding="utf-8")

    result = driver.restore(backup_file)

    assert result.ok is True
    assert calls[0]["args"][0] == "psql"
    assert "--set=ON_ERROR_STOP=1" in calls[0]["args"]
    assert "DROP SCHEMA IF EXISTS public CASCADE;" in calls[0]["args"]
    assert "CREATE SCHEMA public;" in calls[0]["args"]
    assert calls[1]["args"][0] == "psql"
    assert "--set=ON_ERROR_STOP=1" in calls[1]["args"]
    assert "--file" in calls[1]["args"]
    assert calls[0]["env"]["PGPASSWORD"] == "secret"
    assert calls[1]["env"]["PGPASSWORD"] == "secret"


def test_postgresql_driver_stops_when_clean_step_fails(monkeypatch, tmp_path):
    calls = []

    def fake_run(args, *, env=None, input_file=None, output_file=None, timeout_seconds=21600):
        calls.append({"args": args, "env": env})
        from app.drivers.database.base import CommandResult

        return CommandResult(False, 1, "", "permission denied", 0.001)

    monkeypatch.setattr("app.drivers.database.postgresql.run_command", fake_run)
    instance = DatabaseInstance(
        name="postgres",
        db_type="postgresql",
        host="127.0.0.1",
        port=5432,
        username="backup",
        password_encrypted=encrypt_secret("secret"),
        database_name="reports",
        environment="test",
        tags=[],
    )

    backup_file = tmp_path / "backup.sql"
    backup_file.write_text("CREATE TABLE t(id int);\n", encoding="utf-8")

    result = PostgreSQLDriver(instance, "secret").restore(backup_file)

    assert result.ok is False
    assert result.stderr_tail == "permission denied"
    assert len(calls) == 1


def test_postgresql_driver_sanitizes_backup_output_filename(monkeypatch, tmp_path):
    def fake_run(args, *, env=None, input_file=None, output_file=None, timeout_seconds=21600):
        if output_file:
            output_file.write(b"CREATE TABLE t(id int);")
        from app.drivers.database.base import CommandResult

        return CommandResult(True, 0, "PostgreSQL 16", "", 0.001)

    monkeypatch.setattr("app.drivers.database.postgresql.run_command", fake_run)
    instance = DatabaseInstance(
        name="postgres",
        db_type="postgresql",
        host="127.0.0.1",
        port=5432,
        username="backup",
        password_encrypted=encrypt_secret("secret"),
        database_name="../reports",
        environment="test",
        tags=[],
    )

    backup_result = PostgreSQLDriver(instance, "secret").backup(tmp_path)

    assert backup_result.raw_file.parent.resolve() == tmp_path.resolve()
    assert backup_result.raw_file.name == "reports.sql"
