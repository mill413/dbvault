import json

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.encryption import decrypt_secret, encrypt_secret
from app.core.errors import AppError
from app.drivers.registry import registry
from app.models import Storage, User


def encrypt_config(config: dict) -> str:
    return encrypt_secret(json.dumps(config, sort_keys=True))


def decrypt_config(config_encrypted: str) -> dict:
    return json.loads(decrypt_secret(config_encrypted))


def create_storage(db: Session, payload, user: User) -> Storage:
    if payload.is_default:
        db.query(Storage).update({Storage.is_default: False})
    storage = Storage(
        name=payload.name,
        storage_type=payload.storage_type.lower(),
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


def get_default_storage(db: Session) -> Storage:
    storage = (
        db.query(Storage)
        .filter(Storage.deleted_at.is_(None), Storage.status == "ACTIVE", Storage.is_default.is_(True))
        .first()
    )
    if not storage:
        storage = (
            db.query(Storage)
            .filter(Storage.deleted_at.is_(None), Storage.status == "ACTIVE")
            .order_by(Storage.id.asc())
            .first()
        )
    if not storage:
        raise AppError("RESOURCE_NOT_FOUND", "No active storage configured", status_code=404)
    return storage


def build_storage_driver(storage: Storage):
    try:
        driver_cls = registry.get_storage(storage.storage_type)
    except KeyError as exc:
        raise AppError("STORAGE_DRIVER_NOT_FOUND", str(exc), status_code=400) from exc
    return driver_cls(decrypt_config(storage.config_encrypted))

