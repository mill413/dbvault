from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import decode_token, has_permission
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AppError("UNAUTHORIZED", "Missing bearer token", status_code=401)
    payload = decode_token(credentials.credentials)
    user = db.get(User, int(payload["sub"]))
    if not user or user.deleted_at is not None or user.status != "ACTIVE":
        raise AppError("UNAUTHORIZED", "Invalid user", status_code=401)
    if payload.get("ver") != user.token_version:
        raise AppError("UNAUTHORIZED", "Invalid user", status_code=401)
    return user


def require_permission(permission: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, permission):
            raise AppError("FORBIDDEN", "Permission denied", status_code=403)
        return user

    return dependency
