import os
from pathlib import Path
from time import monotonic

from app.drivers.database.base import BackupDriver, BackupResult, elapsed_since
from app.drivers.database.command import run_command


class PostgreSQLDriver(BackupDriver):
    db_type = "postgresql"

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PGPASSWORD"] = self.password
        return env

    def _conn_args(self) -> list[str]:
        return [
            "--host",
            self.instance.host,
            "--port",
            str(self.instance.port),
            "--username",
            self.instance.username,
            "--dbname",
            self.instance.database_name or "postgres",
        ]

    def test_connection(self) -> dict:
        result = run_command(
            ["psql", *self._conn_args(), "--tuples-only", "--no-align", "--command", "SELECT version();"],
            env=self._env(),
            timeout_seconds=15,
        )
        return {
            "ok": result.ok,
            "version": result.stdout_tail.strip() if result.ok else None,
            "duration_seconds": result.duration_seconds,
            "message": result.stderr_tail if not result.ok else None,
        }

    def backup(self, output_dir: Path, timeout_seconds: int = 21600) -> BackupResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        name = self.instance.database_name or "postgres"
        target = output_dir / f"{name}.sql"
        args = ["pg_dump", *self._conn_args(), "--format=plain", "--no-owner", "--no-privileges"]
        start = monotonic()
        with target.open("wb") as output:
            result = run_command(args, env=self._env(), output_file=output, timeout_seconds=timeout_seconds)
        return BackupResult(
            ok=result.ok,
            returncode=result.returncode,
            raw_file=target,
            file_format="sql",
            stdout_tail=result.stdout_tail,
            stderr_tail=result.stderr_tail,
            duration_seconds=elapsed_since(start),
        )

    def restore(self, backup_file: Path, timeout_seconds: int = 21600):
        args = ["psql", *self._conn_args(), "--file", str(backup_file)]
        return run_command(args, env=self._env(), timeout_seconds=timeout_seconds)
