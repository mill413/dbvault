import os
import tempfile
from pathlib import Path
from time import monotonic

from app.drivers.database.base import BackupDriver, BackupResult, elapsed_since
from app.drivers.database.command import run_command
from app.drivers.database.k8s import K8sConfig, run_kubectl_command
from app.utils.paths import safe_filename


class PostgreSQLDriver(BackupDriver):
    db_type = "postgresql"
    _unsupported_restore_lines = {b"SET transaction_timeout = 0;\n"}

    @property
    def _k8s_mode(self) -> bool:
        ct = getattr(self.instance, "connection_type", "direct")
        k8s = getattr(self.instance, "k8s_config", None)
        return ct == "kubernetes" and k8s is not None

    @property
    def _k8s_config(self) -> K8sConfig | None:
        if not self._k8s_mode:
            return None
        return K8sConfig.from_dict(self.instance.k8s_config)

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

    def _k8s_conn_args(self) -> list[str]:
        return [
            "-U", self.instance.username,
            "-d", self.instance.database_name or "postgres",
        ]

    def test_connection(self) -> dict:
        if self._k8s_mode:
            k8s = self._k8s_config
            cmd = ["psql", *self._k8s_conn_args(), "--tuples-only", "--no-align", "-c", "SELECT version();"]
            result = run_kubectl_command(k8s, cmd, env=self._env(), timeout_seconds=15)
            return {
                "ok": result.ok,
                "version": result.stdout_tail.strip() if result.ok else None,
                "duration_seconds": result.duration_seconds,
                "message": result.stderr_tail if not result.ok else None,
            }
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
        name = safe_filename(self.instance.database_name, "postgres")
        target = output_dir / f"{name}.sql"
        if self._k8s_mode:
            k8s = self._k8s_config
            cmd = ["pg_dump", *self._k8s_conn_args(), "--format=plain", "--no-owner", "--no-privileges"]
            start = monotonic()
            with target.open("wb") as output:
                result = run_kubectl_command(
                    k8s, cmd, env=self._env(),
                    output_file=output, timeout_seconds=timeout_seconds,
                )
            return BackupResult(
                ok=result.ok,
                returncode=result.returncode,
                raw_file=target,
                file_format="sql",
                stdout_tail=result.stdout_tail,
                stderr_tail=result.stderr_tail,
                duration_seconds=elapsed_since(start),
            )
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

    def _clean_args(self) -> list[str]:
        """Returns SQL to recreate the public schema before replaying a pg_dump file."""
        return [
            "--set=ON_ERROR_STOP=1",
            "-c", "DROP SCHEMA IF EXISTS public CASCADE;",
            "-c", "CREATE SCHEMA public;",
        ]

    def _compatible_restore_file(self, backup_file: Path) -> Path:
        fd, temp_name = tempfile.mkstemp(prefix=f"{backup_file.stem}-compat-", suffix=backup_file.suffix)
        temp_path = Path(temp_name)
        changed = False
        try:
            with os.fdopen(fd, "wb") as output, backup_file.open("rb") as source:
                for line in source:
                    if line in self._unsupported_restore_lines:
                        changed = True
                        continue
                    output.write(line)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise
        if not changed:
            temp_path.unlink(missing_ok=True)
            return backup_file
        return temp_path

    def restore(self, backup_file: Path, timeout_seconds: int = 21600):
        restore_file = self._compatible_restore_file(backup_file)
        if self._k8s_mode:
            try:
                k8s = self._k8s_config
                # Step 1: clean the database
                clean_cmd = ["psql", *self._k8s_conn_args(), *self._clean_args()]
                clean_result = run_kubectl_command(k8s, clean_cmd, env=self._env(), timeout_seconds=60)
                if not clean_result.ok:
                    return clean_result
                # Step 2: restore
                cmd = ["psql", *self._k8s_conn_args(), "--set=ON_ERROR_STOP=1"]
                with restore_file.open("rb") as input_file:
                    return run_kubectl_command(
                        k8s, cmd, env=self._env(),
                        input_file=input_file, timeout_seconds=timeout_seconds,
                    )
            finally:
                if restore_file != backup_file:
                    restore_file.unlink(missing_ok=True)
        try:
            # Step 1: clean the database
            clean_args = ["psql", *self._conn_args(), *self._clean_args()]
            clean_result = run_command(clean_args, env=self._env(), timeout_seconds=60)
            if not clean_result.ok:
                return clean_result
            # Step 2: restore
            args = ["psql", *self._conn_args(), "--set=ON_ERROR_STOP=1", "--file", str(restore_file)]
            return run_command(args, env=self._env(), timeout_seconds=timeout_seconds)
        finally:
            if restore_file != backup_file:
                restore_file.unlink(missing_ok=True)
