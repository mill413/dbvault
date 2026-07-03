from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.api.pagination import Pagination, pagination_params
from app.core.database import get_db
from app.core.errors import AppError
from app.core.ownership import ensure_owner, is_admin, owner_filter
from app.models import Job, Storage, User
from app.schemas.common import Message, Page
from app.schemas.storages import StorageCapacityResponse, StorageCreate, StorageRead, StorageTestResponse, StorageUpdate
from app.services.audit_service import create_audit_log
from app.services.storage_service import (
    build_storage_driver,
    create_storage,
    encrypt_config,
    ensure_local_storage_root_allowed,
    ensure_storage_name_available,
    get_storage_usage,
)

router = APIRouter()


@router.get("", response_model=Page[StorageRead])
def list_storages(
    pagination: Pagination = Depends(pagination_params),
    storage_type: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("storage:read")),
):
    query = db.query(Storage).filter(Storage.deleted_at.is_(None))
    query = owner_filter(query, Storage, user)
    if storage_type:
        query = query.filter(Storage.storage_type == storage_type.lower())
    if status:
        query = query.filter(Storage.status == status)
    query = query.order_by(Storage.id.asc())
    total = query.count()
    return {
        "items": query.offset((pagination.page - 1) * pagination.page_size).limit(pagination.page_size).all(),
        "page": pagination.page,
        "page_size": pagination.page_size,
        "total": total,
    }


@router.get("/capacity/all", response_model=list[StorageCapacityResponse])
def get_all_storage_capacity(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("storage:read")),
):
    try:
        query = db.query(Storage).filter(Storage.deleted_at.is_(None), Storage.status == "ACTIVE")
        storages = owner_filter(query, Storage, user).all()
    except Exception:
        db.rollback()
        return []
    results = []
    for s in storages:
        try:
            used = get_storage_usage(db, s)
        except Exception:
            db.rollback()
            used = 0
        usage_percent = None
        capacity_limit = getattr(s, "capacity_limit_bytes", None)
        if capacity_limit and capacity_limit > 0:
            usage_percent = round((used / capacity_limit) * 100, 2)
        results.append({
            "storage_id": s.id,
            "storage_name": s.name,
            "capacity_limit_bytes": capacity_limit,
            "used_bytes": used,
            "usage_percent": usage_percent,
        })
    return results


@router.post("", response_model=StorageRead)
def create_storage_endpoint(
    payload: StorageCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("storage:write")),
):
    item = create_storage(db, payload, user)
    create_audit_log(
        db,
        user=user,
        action="storage.create",
        resource_type="storage",
        resource_id=item.id,
        request=request,
    )
    return item


@router.get("/{storage_id}", response_model=StorageRead)
def get_storage(
    storage_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("storage:read")),
):
    item = db.get(Storage, storage_id)
    if not item or item.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Storage not found", status_code=404)
    ensure_owner(item, user, "Storage not found")
    return item


@router.put("/{storage_id}", response_model=StorageRead)
def update_storage(
    storage_id: int,
    payload: StorageUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("storage:write")),
):
    item = db.get(Storage, storage_id)
    if not item or item.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Storage not found", status_code=404)
    ensure_owner(item, user, "Storage not found")
    data = payload.model_dump(exclude_unset=True)
    config = data.pop("config", None)
    if "name" in data:
        ensure_storage_name_available(db, data["name"], exclude_id=item.id)
    if config is not None:
        ensure_local_storage_root_allowed(item.storage_type, config, user)
    for key, value in data.items():
        setattr(item, key, value)
    if config is not None:
        item.config_encrypted = encrypt_config(config)
    if data.get("is_default"):
        query = db.query(Storage)
        if not is_admin(user):
            query = query.filter(Storage.created_by == user.id)
        query.update({Storage.is_default: False})
        item.is_default = True
    db.commit()
    db.refresh(item)
    create_audit_log(
        db,
        user=user,
        action="storage.update",
        resource_type="storage",
        resource_id=item.id,
        request=request,
    )
    return item


@router.delete("/{storage_id}", response_model=Message)
def delete_storage(
    storage_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("storage:write")),
):
    item = db.get(Storage, storage_id)
    if not item or item.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Storage not found", status_code=404)
    ensure_owner(item, user, "Storage not found")
    has_enabled_job = (
        db.query(Job)
        .filter(Job.storage_id == item.id, Job.enabled.is_(True), Job.deleted_at.is_(None))
        .first()
        is not None
    )
    if has_enabled_job:
        raise AppError("VALIDATION_ERROR", "Storage is used by an enabled job", status_code=400)
    item.deleted_at = datetime.now(UTC)
    db.commit()
    create_audit_log(
        db,
        user=user,
        action="storage.delete",
        resource_type="storage",
        resource_id=item.id,
        request=request,
    )
    return {"message": "deleted"}


@router.post("/{storage_id}/test", response_model=StorageTestResponse)
def test_storage(
    storage_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("storage:read")),
):
    item = db.get(Storage, storage_id)
    if not item or item.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Storage not found", status_code=404)
    ensure_owner(item, user, "Storage not found")
    return build_storage_driver(item).test()


@router.get("/{storage_id}/capacity", response_model=StorageCapacityResponse)
def get_storage_capacity(
    storage_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("storage:read")),
):
    item = db.get(Storage, storage_id)
    if not item or item.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Storage not found", status_code=404)
    ensure_owner(item, user, "Storage not found")
    try:
        used = get_storage_usage(db, item)
    except Exception:
        db.rollback()
        used = 0
    usage_percent = None
    capacity_limit = getattr(item, "capacity_limit_bytes", None)
    if capacity_limit and capacity_limit > 0:
        usage_percent = round((used / capacity_limit) * 100, 2)
    return {
        "storage_id": item.id,
        "storage_name": item.name,
        "capacity_limit_bytes": capacity_limit,
        "used_bytes": used,
        "usage_percent": usage_percent,
    }
