from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import hash_password
from app.models import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.common import Message
from app.schemas.users import UserRead
from app.services.audit_service import create_audit_log
from app.services.auth_service import (
    authenticate_user,
    build_token_response,
    change_password,
    refresh_tokens,
)

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    try:
        user = authenticate_user(db, payload.username, payload.password)
    except AppError as exc:
        create_audit_log(
            db,
            user=None,
            action="auth.login",
            request=request,
            result="failed",
            reason=exc.message,
            metadata={"username": payload.username},
        )
        raise
    create_audit_log(db, user=user, action="auth.login", request=request)
    return build_token_response(user)


@router.post("/register", response_model=UserRead)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.enable_registration:
        raise AppError("REGISTRATION_DISABLED", "User registration is disabled", status_code=403)
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise AppError("VALIDATION_ERROR", "Username already exists", status_code=409)
    if payload.email:
        existing_email = db.query(User).filter(User.email == payload.email).first()
        if existing_email:
            raise AppError("VALIDATION_ERROR", "Email already registered", status_code=409)
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        email=payload.email,
        role="User",
        status="ACTIVE",
        password_changed_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    create_audit_log(
        db,
        user=user,
        action="auth.register",
        request=request,
        metadata={"username": payload.username},
    )
    return user


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    return refresh_tokens(db, payload.refresh_token)


@router.post("/logout", response_model=Message)
def logout(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    create_audit_log(db, user=user, action="auth.logout", request=request)
    return {"message": "logged out"}


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password", response_model=Message)
def change_own_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    change_password(db, user, payload.old_password, payload.new_password)
    create_audit_log(db, user=user, action="auth.change_password", request=request)
    return {"message": "password changed"}


@router.get("/public-config")
def public_config():
    settings = get_settings()
    return {"registration_enabled": settings.enable_registration}
