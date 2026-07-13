from sqlalchemy.orm import Session

from app.core.encryption import decrypt_secret, encrypt_secret
from app.core.errors import AppError
from app.drivers.registry import registry
from app.models import DatabaseInstance, User


def ensure_database_name_available(db: Session, name: str, *, exclude_id: int | None = None) -> None:
    query = db.query(DatabaseInstance).filter(DatabaseInstance.name == name, DatabaseInstance.deleted_at.is_(None))
    if exclude_id is not None:
        query = query.filter(DatabaseInstance.id != exclude_id)
    if query.first():
        raise AppError("ALREADY_EXISTS", f"Database instance '{name}' already exists", status_code=409)


def create_database(db: Session, payload, user: User) -> DatabaseInstance:
    ensure_database_name_available(db, payload.name)
    k8s_data = None
    if hasattr(payload, "k8s_config") and payload.k8s_config is not None:
        k8s_data = payload.k8s_config.model_dump() if hasattr(payload.k8s_config, "model_dump") else payload.k8s_config
    is_k8s = getattr(payload, "connection_type", "direct") == "kubernetes"
    instance = DatabaseInstance(
        name=payload.name,
        db_type=payload.db_type.lower(),
        host=payload.host if not is_k8s else "",
        port=payload.port if not is_k8s else 0,
        username=payload.username,
        password_encrypted=encrypt_secret(payload.password),
        database_name=payload.database_name,
        ssl_enabled=payload.ssl_enabled,
        ssl_config=payload.ssl_config,
        environment=payload.environment,
        owner=payload.owner,
        tags=payload.tags,
        description=payload.description,
        connection_type=getattr(payload, "connection_type", "direct"),
        k8s_config=k8s_data,
        created_by=user.id,
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


def update_database(db: Session, instance: DatabaseInstance, payload) -> DatabaseInstance:
    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    if "name" in data:
        ensure_database_name_available(db, data["name"], exclude_id=instance.id)
    conn_type = data.get("connection_type", instance.connection_type)
    if conn_type == "kubernetes":
        if "host" in data and data["host"] is None:
            data["host"] = ""
        if "port" in data and data["port"] is None:
            data["port"] = 0
    for key, value in data.items():
        setattr(instance, key, value)
    if password is not None:
        instance.password_encrypted = encrypt_secret(password)
    return instance


def build_database_driver(instance: DatabaseInstance):
    try:
        driver_cls = registry.get_database(instance.db_type)
    except KeyError as exc:
        raise AppError("DATABASE_DRIVER_NOT_FOUND", str(exc), status_code=400) from exc
    return driver_cls(instance, decrypt_secret(instance.password_encrypted))

def test_database_connection(instance: DatabaseInstance) -> dict:
    return build_database_driver(instance).test_connection()
