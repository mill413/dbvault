from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.api.pagination import Pagination, pagination_params
from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import hash_password
from app.models import User
from app.schemas.common import Message, Page
from app.schemas.users import ResetPasswordRequest, UserCreate, UserRead, UserUpdate
from app.services.audit_service import create_audit_log

router = APIRouter()


@router.get("", response_model=Page[UserRead])
def list_users(
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("user:read")),
):
    query = db.query(User).filter(User.deleted_at.is_(None)).order_by(User.id.asc())
    total = query.count()
    items = query.offset((pagination.page - 1) * pagination.page_size).limit(pagination.page_size).all()
    return {"items": items, "page": pagination.page, "page_size": pagination.page_size, "total": total}


@router.post("", response_model=UserRead)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("user:write")),
):
    created = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        email=payload.email,
        role=payload.role,
        status="ACTIVE",
        password_changed_at=datetime.now(UTC),
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    create_audit_log(db, user=user, action="user.create", resource_type="user", resource_id=created.id, request=request)
    return created


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("user:read"))):
    item = db.get(User, user_id)
    if not item or item.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "User not found", status_code=404)
    return item


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("user:write")),
):
    item = db.get(User, user_id)
    if not item or item.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "User not found", status_code=404)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    create_audit_log(db, user=user, action="user.update", resource_type="user", resource_id=item.id, request=request)
    return item


@router.delete("/{user_id}", response_model=Message)
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("user:write")),
):
    item = db.get(User, user_id)
    if not item or item.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "User not found", status_code=404)
    item.deleted_at = datetime.now(UTC)
    db.commit()
    create_audit_log(db, user=user, action="user.delete", resource_type="user", resource_id=item.id, request=request)
    return {"message": "deleted"}


@router.post("/{user_id}/reset-password", response_model=Message)
def reset_password(
    user_id: int,
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("user:write")),
):
    item = db.get(User, user_id)
    if not item or item.deleted_at is not None:
        raise AppError("RESOURCE_NOT_FOUND", "User not found", status_code=404)
    item.password_hash = hash_password(payload.password)
    item.password_changed_at = datetime.now(UTC)
    item.token_version += 1
    db.commit()
    create_audit_log(
        db,
        user=user,
        action="user.reset_password",
        resource_type="user",
        resource_id=item.id,
        request=request,
    )
    return {"message": "password reset"}
