import re
from datetime import datetime


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9_-]+", "-", value)
    return value.strip("-") or "unknown"


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
        f"{timestamp:%Y/%m/%d}/{backup_id}-{timestamp:%Y%m%dT%H%M%S}.{extension.lstrip('.')}"
    )

