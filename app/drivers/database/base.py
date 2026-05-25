from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from app.models import DatabaseInstance


@dataclass
class CommandResult:
    ok: bool
    returncode: int
    stdout_tail: str
    stderr_tail: str
    duration_seconds: float


@dataclass
class BackupResult:
    ok: bool
    returncode: int
    raw_file: Path
    file_format: str
    stdout_tail: str
    stderr_tail: str
    duration_seconds: float
    database_version: str | None = None


class BackupDriver:
    db_type = "base"

    def __init__(self, instance: DatabaseInstance, password: str) -> None:
        self.instance = instance
        self.password = password

    def test_connection(self) -> dict:
        raise NotImplementedError

    def backup(self, output_dir: Path, timeout_seconds: int = 21600) -> BackupResult:
        raise NotImplementedError

    def restore(self, backup_file: Path, timeout_seconds: int = 21600) -> CommandResult:
        raise NotImplementedError


def tail_text(value: bytes, limit: int = 8000) -> str:
    return value.decode("utf-8", errors="replace")[-limit:]


def elapsed_since(start: float) -> float:
    return round(monotonic() - start, 3)
