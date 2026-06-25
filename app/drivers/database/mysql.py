import os
from pathlib import Path
from time import monotonic

from app.drivers.database.base import BackupDriver, BackupResult, elapsed_since
from app.drivers.database.command import run_command
from app.drivers.database.k8s import K8sConfig, run_kubectl_command


class MySQLDriver(BackupDriver):
    db_type = "mysql"

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

    def _dump_database_args(self) -> list[str]:
        if self.instance.database_name:
            return [self.instance.database_name]
        return ["--all-databases"]

    def test_connection(self) -> dict:
        if self._k8s_mode:
            k8s = self._k8s_config
            cmd = ["mysql", "-u", self.instance.username, "--batch", "--skip-column-names", "-e", "SELECT VERSION();"]
            if self.instance.database_name:
                cmd.append(self.instance.database_name)
            result = run_kubectl_command(k8s, cmd, env=self._env(), timeout_seconds=15)
            return {
                "ok": result.ok,
                "version": result.stdout_tail.strip() if result.ok else None,
                "duration_seconds": result.duration_seconds,
                "message": result.stderr_tail if not result.ok else None,
            }
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
        if self._k8s_mode:
            k8s = self._k8s_config
            cmd = [
                "mysqldump", "-u", self.instance.username,
                "--single-transaction", "--routines", "--triggers",
                "--events", "--hex-blob",
            ]
            cmd += self._dump_database_args()
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
        args = self._base_args("mysqldump") + [
            "--single-transaction",
            "--routines",
            "--triggers",
            "--events",
            "--hex-blob",
        ]
        args += self._dump_database_args()
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
        if self._k8s_mode:
            k8s = self._k8s_config
            cmd = ["mysql", "-u", self.instance.username]
            if self.instance.database_name:
                cmd.append(self.instance.database_name)
            with backup_file.open("rb") as input_file:
                return run_kubectl_command(
                    k8s, cmd, env=self._env(),
                    input_file=input_file, timeout_seconds=timeout_seconds,
                )
        args = self._base_args("mysql")
        if self.instance.database_name:
            args.append(self.instance.database_name)
        with backup_file.open("rb") as input_file:
            return run_command(args, env=self._env(), input_file=input_file, timeout_seconds=timeout_seconds)


class MariaDBDriver(MySQLDriver):
    db_type = "mariadb"
