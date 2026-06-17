from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.errors import AppError


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_token(subject: str, claims: dict[str, Any] | None = None, token_type: str = "access") -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    expire_minutes = (
        settings.access_token_expire_minutes
        if token_type == "access"
        else settings.refresh_token_expire_minutes
    )
    payload = {
        "sub": subject,
        "type": token_type,
        "jti": str(uuid4()),
        "iat": int(now.timestamp()),
        "exp": now + timedelta(minutes=expire_minutes),
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise AppError("UNAUTHORIZED", "Invalid token", status_code=401) from exc
    if payload.get("type") != expected_type:
        raise AppError("UNAUTHORIZED", "Invalid token type", status_code=401)
    return payload


ROLE_PERMISSIONS = {
    "Admin": {
        "user:read",
        "user:write",
        "database:read",
        "database:write",
        "backup:read",
        "backup:run",
        "backup:delete",
        "restore:run",
        "job:read",
        "job:write",
        "storage:read",
        "storage:write",
        "audit:read",
    },
    "User": {
        "database:read",
        "database:write",
        "backup:read",
        "backup:run",
        "backup:delete",
        "restore:run",
        "job:read",
        "job:write",
        "storage:read",
        "storage:write",
    },
}


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
