from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models import User


def ensure_initial_admin(db: Session) -> None:
    settings = get_settings()
    exists = db.query(User).filter(User.username == settings.initial_admin_username).first()
    if exists:
        return
    db.add(
        User(
            username=settings.initial_admin_username,
            password_hash=hash_password(settings.initial_admin_password),
            display_name="Initial Admin",
            role="Admin",
            status="ACTIVE",
            password_changed_at=datetime.now(UTC),
        )
    )
    db.commit()


def authenticate_user(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter(User.username == username, User.deleted_at.is_(None)).first()
    if not user or user.status != "ACTIVE" or not verify_password(password, user.password_hash):
        raise AppError("UNAUTHORIZED", "Invalid username or password", status_code=401)
    user.last_login_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)
    return user


def build_token_response(user: User) -> dict:
    settings = get_settings()
    claims = {"username": user.username, "role": user.role}
    return {
        "access_token": create_token(str(user.id), claims, "access"),
        "refresh_token": create_token(str(user.id), claims, "refresh"),
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": user,
    }


def refresh_tokens(db: Session, refresh_token: str) -> dict:
    payload = decode_token(refresh_token, expected_type="refresh")
    user = db.get(User, int(payload["sub"]))
    if not user or user.deleted_at is not None or user.status != "ACTIVE":
        raise AppError("UNAUTHORIZED", "Invalid refresh token", status_code=401)
    return build_token_response(user)


def change_password(db: Session, user: User, old_password: str, new_password: str) -> None:
    if not verify_password(old_password, user.password_hash):
        raise AppError("VALIDATION_ERROR", "Old password is incorrect", status_code=400)
    user.password_hash = hash_password(new_password)
    user.password_changed_at = datetime.now(UTC)
    db.commit()

