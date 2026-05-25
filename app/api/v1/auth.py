from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshRequest, TokenResponse
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
    user = authenticate_user(db, payload.username, payload.password)
    create_audit_log(db, user=user, action="auth.login", request=request)
    return build_token_response(user)


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

