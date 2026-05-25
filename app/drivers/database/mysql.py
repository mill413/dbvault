import os
from pathlib import Path
from time import monotonic

from app.drivers.database.base import BackupDriver, BackupResult, elapsed_since
from app.drivers.database.command import run_command


class MySQLDriver(BackupDriver):
    db_type = "mysql"

    def _base_args(self, binary: str) -> list[str]:
        return [
            binary,
            "--host",
            self.instance.host,
            "--port",
            str(self.instance.port),
            "--user",
            self.instance.username,
        ]

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["MYSQL_PWD"] = self.password
        return env

    def test_connection(self) -> dict:
        result = run_command(
            self._base_args("mysql")
            + ["--connect-timeout=10", "--batch", "--skip-column-names", "-e", "SELECT VERSION();"],
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
        name = self.instance.database_name or "all-databases"
        target = output_dir / f"{name}.sql"
        args = self._base_args("mysqldump") + [
            "--single-transaction",
            "--routines",
            "--triggers",
            "--events",
            "--hex-blob",
            "--set-gtid-purged=OFF",
        ]
        if self.instance.database_name:
            args += ["--databases", self.instance.database_name]
        else:
            args.append("--all-databases")
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
        args = self._base_args("mysql")
        if self.instance.database_name:
            args.append(self.instance.database_name)
        with backup_file.open("rb") as input_file:
            return run_command(args, env=self._env(), input_file=input_file, timeout_seconds=timeout_seconds)


class MariaDBDriver(MySQLDriver):
    db_type = "mariadb"
