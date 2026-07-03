import re
from datetime import datetime
from pathlib import Path


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9_-]+", "-", value)
    return value.strip("-") or "unknown"


def safe_filename(value: str | None, default: str = "backup") -> str:
    if not value:
        return default
    filename = Path(value).name
    stem, dot, suffix = filename.partition(".")
    safe_stem = slugify(stem)
    if not dot:
        return safe_stem
    safe_suffix = re.sub(r"[^a-zA-Z0-9._-]+", "-", suffix).strip(".-")
    return f"{safe_stem}.{safe_suffix}" if safe_suffix else safe_stem


def safe_extension(value: str | None, default: str = "bin") -> str:
    if not value:
        return default
    extension = value.rsplit(".", 1)[-1] if "." in value else value
    extension = re.sub(r"[^a-zA-Z0-9._-]+", "-", extension).strip(".-")
    return extension or default


def safe_join(root: Path, filename: str) -> Path:
    root = root.resolve()
    target = (root / safe_filename(filename)).resolve()
    if not target.is_relative_to(root):
        raise ValueError("Path escapes root")
    return target


def build_backup_object_key(
    db_type: str,
    environment: str,
    database_name: str,
    backup_id: int,
    timestamp: datetime,
    extension: str,
) -> str:
    return (
        f"{slugify(db_type)}/{slugify(environment)}/{slugify(database_name)}/"
        f"{timestamp:%Y/%m/%d}/{backup_id}-{timestamp:%Y%m%dT%H%M%S}.{safe_extension(extension)}"
    )
