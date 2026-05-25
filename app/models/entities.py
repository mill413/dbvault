from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128))
    email: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DatabaseInstance(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "database_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    db_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    database_name: Mapped[str | None] = mapped_column(String(128))
    ssl_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ssl_config: Mapped[dict | None] = mapped_column(JSON)
    environment: Mapped[str] = mapped_column(String(32), default="prod", nullable=False, index=True)
    owner: Mapped[str | None] = mapped_column(String(128))
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class Storage(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "storages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    storage_type: Mapped[str] = mapped_column(String(32), nullable=False)
    config_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class Backup(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "backups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    database_id: Mapped[int] = mapped_column(ForeignKey("database_instances.id"), nullable=False)
    storage_id: Mapped[int] = mapped_column(ForeignKey("storages.id"), nullable=False)
    backup_task_id: Mapped[int | None] = mapped_column(ForeignKey("backup_tasks.id"))
    backup_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_format: Mapped[str] = mapped_column(String(32), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    compressed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    compression: Mapped[str | None] = mapped_column(String(32))
    md5: Mapped[str | None] = mapped_column(String(64))
    sha256: Mapped[str] = mapped_column(String(128), nullable=False)
    database_version: Mapped[str | None] = mapped_column(String(255))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    database: Mapped[DatabaseInstance] = relationship()
    storage: Mapped[Storage] = relationship()


class BackupTask(Base, TimestampMixin):
    __tablename__ = "backup_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    database_id: Mapped[int] = mapped_column(ForeignKey("database_instances.id"), nullable=False)
    storage_id: Mapped[int] = mapped_column(ForeignKey("storages.id"), nullable=False)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    phase: Mapped[str | None] = mapped_column(String(32))
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    stdout_tail: Mapped[str | None] = mapped_column(Text)
    stderr_tail: Mapped[str | None] = mapped_column(Text)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(12, 3))
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    database: Mapped[DatabaseInstance] = relationship()
    storage: Mapped[Storage] = relationship()


class RestoreTask(Base, TimestampMixin):
    __tablename__ = "restore_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    backup_id: Mapped[int] = mapped_column(ForeignKey("backups.id"), nullable=False)
    source_database_id: Mapped[int | None] = mapped_column(ForeignKey("database_instances.id"))
    target_database_id: Mapped[int | None] = mapped_column(ForeignKey("database_instances.id"))
    restore_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    phase: Mapped[str | None] = mapped_column(String(32))
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirm_text: Mapped[str | None] = mapped_column(String(255))
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    stdout_tail: Mapped[str | None] = mapped_column(Text)
    stderr_tail: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(12, 3))
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    backup: Mapped[Backup] = relationship()
    target_database: Mapped[DatabaseInstance | None] = relationship(
        foreign_keys=[target_database_id]
    )


class Job(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    database_id: Mapped[int] = mapped_column(ForeignKey("database_instances.id"), nullable=False)
    storage_id: Mapped[int] = mapped_column(ForeignKey("storages.id"), nullable=False)
    schedule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    cron_expr: Mapped[str | None] = mapped_column(String(128))
    interval_seconds: Mapped[int | None] = mapped_column(Integer)
    run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_concurrent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retention_policy: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    backup_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(32))
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    database: Mapped[DatabaseInstance] = relationship()
    storage: Mapped[Storage] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TaskEvent(Base):
    __tablename__ = "task_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    task_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(32), nullable=False)
    phase: Mapped[str | None] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", nullable=False, index=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

