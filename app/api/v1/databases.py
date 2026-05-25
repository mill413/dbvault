from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.core.errors import AppError
from app.models import DatabaseInstance, User
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


@router.get("", response_model=Page[DatabaseRead])
def list_databases(
    page: int = 1,
    page_size: int = 20,
    db_type: str | None = None,
    environment: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("database:read")),
):
    query = db.query(DatabaseInstance).filter(DatabaseInstance.deleted_at.is_(None))
    if db_type:
        query = query.filter(DatabaseInstance.db_type == db_type.lower())
    if environment:
        query = query.filter(DatabaseInstance.environment == environment)
    total = query.count()
    items = query.order_by(DatabaseInstance.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.post("", response_model=DatabaseRead)
def create_database_endpoint(
    payload: DatabaseCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("database:write")),
):
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
    item = create_database(db, payload, user)
    result = test_database_connection(item)
    item.deleted_at = datetime.now(UTC)
    db.commit()
    return result


@router.get("/{database_id}", response_model=DatabaseRead)
def get_database_endpoint(
    database_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("database:read")),
):
    item = db.get(DatabaseInstance, database_id)
    if not item or item.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Database instance not found", status_code=404)
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
    update_database(item, payload)
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
    _: User = Depends(require_permission("database:read")),
):
    item = db.get(DatabaseInstance, database_id)
    if not item or item.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "Database instance not found", status_code=404)
    return test_database_connection(item)
