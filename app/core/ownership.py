from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Query

from app.core.errors import AppError
from app.models import User


def is_admin(user: User) -> bool:
    return user.role == "Admin"


def owner_filter(query: Query, model: Any, user: User) -> Query:
    if is_admin(user):
        return query
    return query.filter(model.created_by == user.id)


def ensure_owner(resource: Any, user: User, message: str = "Resource not found") -> None:
    if is_admin(user):
        return
    if getattr(resource, "created_by", None) != user.id:
        raise AppError("RESOURCE_NOT_FOUND", message, status_code=404)


def alert_owner_filter(query: Query, user: User) -> Query:
    if is_admin(user):
        return query
    from app.models import Alert, Backup, BackupTask, DatabaseInstance, RestoreTask, Storage

    conditions = []
    for resource_type, model in (
        ("database", DatabaseInstance),
        ("database_instance", DatabaseInstance),
        ("storage", Storage),
        ("backup", Backup),
        ("backup_task", BackupTask),
        ("restore_task", RestoreTask),
    ):
        ids = [str(item_id) for (item_id,) in query.session.query(model.id).filter(model.created_by == user.id).all()]
        if ids:
            conditions.append((Alert.resource_type == resource_type) & Alert.resource_id.in_(ids))
    if not conditions:
        return query.filter(False)
    return query.filter(or_(*conditions))
