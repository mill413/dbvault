import json
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.encryption import decrypt_secret, encrypt_secret
from app.core.errors import AppError
from app.core.ownership import is_admin
from app.drivers.registry import registry
from app.models import Storage, User


def encrypt_config(config: dict) -> str:
    return encrypt_secret(json.dumps(config, sort_keys=True))


def decrypt_config(config_encrypted: str) -> dict:
    return json.loads(decrypt_secret(config_encrypted))


def ensure_storage_name_available(db: Session, name: str, *, exclude_id: int | None = None) -> None:
    query = db.query(Storage).filter(Storage.name == name, Storage.deleted_at.is_(None))
    if exclude_id is not None:
        query = query.filter(Storage.id != exclude_id)
    if query.first():
        raise AppError("ALREADY_EXISTS", f"Storage '{name}' already exists", status_code=409)


def ensure_local_storage_root_allowed(storage_type: str, config: dict | None, user: User) -> None:
    if storage_type.lower() != "local" or is_admin(user) or not config:
        return
    configured = config.get("root_path") or config.get("path")
    if not configured:
        return
    root = Path(configured).expanduser().resolve()
    allowed_root = get_settings().local_storage_root.expanduser().resolve()
    if not root.is_relative_to(allowed_root):
        raise AppError(
            "VALIDATION_ERROR",
            f"Local storage root must be inside {allowed_root}",
            status_code=400,
        )


def create_storage(db: Session, payload, user: User) -> Storage:
    storage_type = payload.storage_type.lower()
    ensure_storage_name_available(db, payload.name)
    ensure_local_storage_root_allowed(storage_type, payload.config, user)
    if payload.is_default:
        query = db.query(Storage)
        if not is_admin(user):
            query = query.filter(Storage.created_by == user.id)
        query.update({Storage.is_default: False})
    storage = Storage(
        name=payload.name,
        storage_type=storage_type,
        config_encrypted=encrypt_config(payload.config),
        is_default=payload.is_default,
        capacity_limit_bytes=getattr(payload, "capacity_limit_bytes", None),
        created_by=user.id,
    )
    db.add(storage)
    db.commit()
    db.refresh(storage)
    return storage


def get_storage_usage(db: Session, storage: Storage) -> int:
    from app.models import Backup
    result = (
        db.query(func.coalesce(func.sum(Backup.size_bytes), 0))
        .filter(Backup.storage_id == storage.id, Backup.deleted_at.is_(None))
        .scalar()
    )
    return int(result)


def get_default_storage(db: Session, user: User | None = None) -> Storage:
    query = db.query(Storage).filter(Storage.deleted_at.is_(None), Storage.status == "ACTIVE")
    if user is not None and not is_admin(user):
        query = query.filter(Storage.created_by == user.id)
    storage = query.filter(Storage.is_default.is_(True)).first()
    if not storage:
        storage = query.order_by(Storage.id.asc()).first()
    if not storage:
        raise AppError("RESOURCE_NOT_FOUND", "No active storage configured", status_code=404)
    return storage


def build_storage_driver(storage: Storage):
    try:
        driver_cls = registry.get_storage(storage.storage_type)
    except KeyError as exc:
        raise AppError("STORAGE_DRIVER_NOT_FOUND", str(exc), status_code=400) from exc
    return driver_cls(decrypt_config(storage.config_encrypted))
