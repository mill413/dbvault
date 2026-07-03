import json
import os
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.api.pagination import Pagination, pagination_params
from app.core.database import get_db
from app.core.errors import AppError
from app.core.ownership import ensure_owner, is_admin, owner_filter
from app.drivers.database.k8s import list_namespaces, list_pods
from app.models import DatabaseInstance, Job, User
from app.schemas.common import Message, Page
from app.schemas.databases import (
    ConnectionTestResponse,
    DatabaseCreate,
    DatabaseRead,
    DatabaseTestRequest,
    DatabaseUpdate,
)
from app.services.audit_service import create_audit_log
from app.services.database_service import (
    create_database,
    test_database_connection,
    update_database,
)

router = APIRouter()

KUBECONFIG_DIR = Path(os.getenv("DBVAULT_KUBECONFIG_DIR", "/var/lib/dbvault/kubeconfigs"))


def _ensure_kubeconfig_access(kubeconfig: str | None, user: User) -> None:
    if not kubeconfig or is_admin(user):
        return
    path = Path(kubeconfig).resolve()
    root = KUBECONFIG_DIR.resolve()
    if not path.is_relative_to(root):
        raise AppError("RESOURCE_NOT_FOUND", "Kubeconfig not found", status_code=404)
    metadata_path = path.with_suffix(path.suffix + ".meta.json")
    try:
        owner_id = json.loads(metadata_path.read_text(encoding="utf-8")).get("created_by")
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        owner_id = None
    if owner_id != user.id:
        raise AppError("RESOURCE_NOT_FOUND", "Kubeconfig not found", status_code=404)


@router.get("", response_model=Page[DatabaseRead])
def list_databases(
    pagination: Pagination = Depends(pagination_params),
    name: str | None = None,
    db_type: str | None = None,
    environment: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("database:read")),
):
    query = db.query(DatabaseInstance).filter(DatabaseInstance.deleted_at.is_(None))
    query = owner_filter(query, DatabaseInstance, user)
    if name:
        query = query.filter(DatabaseInstance.name.ilike(f"%{name}%"))
    if db_type:
        query = query.filter(DatabaseInstance.db_type == db_type.lower())
    if environment:
        query = query.filter(DatabaseInstance.environment == environment)
    total = query.count()
    items = (
        query.order_by(DatabaseInstance.id.desc())
        .offset((pagination.page - 1) * pagination.page_size)
        .limit(pagination.page_size)
        .all()
    )
    return {"items": items, "page": pagination.page, "page_size": pagination.page_size, "total": total}


@router.post("", response_model=DatabaseRead)
def create_database_endpoint(
    payload: DatabaseCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("database:write")),
):
    if payload.k8s_config:
        _ensure_kubeconfig_access(payload.k8s_config.kubeconfig, user)
    item = create_database(db, payload, user)
    create_audit_log(
        db,
        user=user,
        action="database.create",
        resource_type="database",
        resource_id=item.id,
        request=request,
    )
    return item


@router.post("/test", response_model=ConnectionTestResponse)
def test_temporary_database(
    payload: DatabaseTestRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("database:write")),
):
    if payload.k8s_config:
        _ensure_kubeconfig_access(payload.k8s_config.kubeconfig, user)
    item = create_database(db, payload, user)
    result = test_database_connection(item)
    item.deleted_at = datetime.now(UTC)
    db.commit()
    return result


@router.get("/k8s/namespaces")
def get_k8s_namespaces(
    kubeconfig: str | None = None,
    context: str | None = None,
    user: User = Depends(require_permission("database:read")),
):
    _ensure_kubeconfig_access(kubeconfig, user)
    namespaces = list_namespaces(kubeconfig=kubeconfig, context=context)
    return {"namespaces": namespaces}


@router.get("/k8s/pods")
def get_k8s_pods(
    namespace: str = "default",
    kubeconfig: str | None = None,
    context: str | None = None,
    user: User = Depends(require_permission("database:read")),
):
    _ensure_kubeconfig_access(kubeconfig, user)
    pods = list_pods(namespace=namespace, kubeconfig=kubeconfig, context=context)
    return {"pods": pods}


@router.get("/{database_id}", response_model=DatabaseRead)
def get_database_endpoint(
    database_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("database:read")),
):
    item = db.get(DatabaseInstance, database_id)
    if not item or item.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Database instance not found", status_code=404)
    ensure_owner(item, user, "Database instance not found")
    return item


@router.put("/{database_id}", response_model=DatabaseRead)
def update_database_endpoint(
    database_id: int,
    payload: DatabaseUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("database:write")),
):
    item = db.get(DatabaseInstance, database_id)
    if not item or item.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Database instance not found", status_code=404)
    ensure_owner(item, user, "Database instance not found")
    if payload.k8s_config:
        _ensure_kubeconfig_access(payload.k8s_config.kubeconfig, user)
    update_database(db, item, payload)
    db.commit()
    db.refresh(item)
    create_audit_log(
        db,
        user=user,
        action="database.update",
        resource_type="database",
        resource_id=item.id,
        request=request,
    )
    return item


@router.delete("/{database_id}", response_model=Message)
def delete_database_endpoint(
    database_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("database:write")),
):
    item = db.get(DatabaseInstance, database_id)
    if not item or item.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Database instance not found", status_code=404)
    ensure_owner(item, user, "Database instance not found")
    has_enabled_job = (
        db.query(Job)
        .filter(Job.database_id == item.id, Job.enabled.is_(True), Job.deleted_at.is_(None))
        .first()
        is not None
    )
    if has_enabled_job:
        raise AppError("VALIDATION_ERROR", "Database instance is used by an enabled job", status_code=400)
    item.deleted_at = datetime.now(UTC)
    db.commit()
    create_audit_log(
        db,
        user=user,
        action="database.delete",
        resource_type="database",
        resource_id=item.id,
        request=request,
    )
    return {"message": "deleted"}


@router.post("/{database_id}/test", response_model=ConnectionTestResponse)
def test_saved_database(
    database_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("database:read")),
):
    item = db.get(DatabaseInstance, database_id)
    if not item or item.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Database instance not found", status_code=404)
    ensure_owner(item, user, "Database instance not found")
    return test_database_connection(item)
