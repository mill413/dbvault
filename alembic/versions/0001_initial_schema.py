"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-25 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    ]


def _soft_delete_column() -> sa.Column:
    return sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamp_columns(),
        _soft_delete_column(),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)

    op.create_table(
        "database_instances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("db_type", sa.String(32), nullable=False),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(128), nullable=False),
        sa.Column("password_encrypted", sa.Text(), nullable=False),
        sa.Column("database_name", sa.String(128), nullable=True),
        sa.Column("ssl_enabled", sa.Boolean(), nullable=False),
        sa.Column("ssl_config", sa.JSON(), nullable=True),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("owner", sa.String(128), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        *_timestamp_columns(),
        _soft_delete_column(),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_database_instances_db_type"), "database_instances", ["db_type"], unique=False)
    op.create_index(op.f("ix_database_instances_environment"), "database_instances", ["environment"], unique=False)
    op.create_index(op.f("ix_database_instances_name"), "database_instances", ["name"], unique=False)

    op.create_table(
        "storages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("storage_type", sa.String(32), nullable=False),
        sa.Column("config_encrypted", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        *_timestamp_columns(),
        _soft_delete_column(),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_storages_name"), "storages", ["name"], unique=False)

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("database_id", sa.Integer(), sa.ForeignKey("database_instances.id"), nullable=False),
        sa.Column("storage_id", sa.Integer(), sa.ForeignKey("storages.id"), nullable=False),
        sa.Column("schedule_type", sa.String(32), nullable=False),
        sa.Column("cron_expr", sa.String(128), nullable=True),
        sa.Column("interval_seconds", sa.Integer(), nullable=True),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("allow_concurrent", sa.Boolean(), nullable=False),
        sa.Column("retention_policy", sa.JSON(), nullable=False),
        sa.Column("backup_config", sa.JSON(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(32), nullable=True),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        *_timestamp_columns(),
        _soft_delete_column(),
    )

    op.create_table(
        "backup_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("database_id", sa.Integer(), sa.ForeignKey("database_instances.id"), nullable=False),
        sa.Column("storage_id", sa.Integer(), sa.ForeignKey("storages.id"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("phase", sa.String(32), nullable=True),
        sa.Column("trigger_type", sa.String(32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("stdout_tail", sa.Text(), nullable=True),
        sa.Column("stderr_tail", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(12, 3), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamp_columns(),
    )
    op.create_index(op.f("ix_backup_tasks_status"), "backup_tasks", ["status"], unique=False)

    op.create_table(
        "backups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("database_id", sa.Integer(), sa.ForeignKey("database_instances.id"), nullable=False),
        sa.Column("storage_id", sa.Integer(), sa.ForeignKey("storages.id"), nullable=False),
        sa.Column("backup_task_id", sa.Integer(), sa.ForeignKey("backup_tasks.id"), nullable=True),
        sa.Column("backup_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_format", sa.String(32), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("compressed", sa.Boolean(), nullable=False),
        sa.Column("compression", sa.String(32), nullable=True),
        sa.Column("md5", sa.String(64), nullable=True),
        sa.Column("sha256", sa.String(128), nullable=False),
        sa.Column("database_version", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        *_timestamp_columns(),
        _soft_delete_column(),
    )
    op.create_index(op.f("ix_backups_expires_at"), "backups", ["expires_at"], unique=False)
    op.create_index(op.f("ix_backups_status"), "backups", ["status"], unique=False)

    op.create_table(
        "restore_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("backup_id", sa.Integer(), sa.ForeignKey("backups.id"), nullable=False),
        sa.Column("source_database_id", sa.Integer(), sa.ForeignKey("database_instances.id"), nullable=True),
        sa.Column("target_database_id", sa.Integer(), sa.ForeignKey("database_instances.id"), nullable=True),
        sa.Column("restore_mode", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("phase", sa.String(32), nullable=True),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("confirm_text", sa.String(255), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("stdout_tail", sa.Text(), nullable=True),
        sa.Column("stderr_tail", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(12, 3), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamp_columns(),
    )
    op.create_index(op.f("ix_restore_tasks_status"), "restore_tasks", ["status"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)

    op.create_table(
        "task_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_type", sa.String(32), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(32), nullable=False),
        sa.Column("phase", sa.String(32), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index(op.f("ix_task_events_task_id"), "task_events", ["task_id"], unique=False)
    op.create_index(op.f("ix_task_events_task_type"), "task_events", ["task_type"], unique=False)

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alert_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("dedupe_key", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_alerts_dedupe_key"), "alerts", ["dedupe_key"], unique=False)
    op.create_index(op.f("ix_alerts_status"), "alerts", ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("task_events")
    op.drop_table("audit_logs")
    op.drop_table("restore_tasks")
    op.drop_table("backups")
    op.drop_table("backup_tasks")
    op.drop_table("jobs")
    op.drop_table("storages")
    op.drop_table("database_instances")
    op.drop_table("users")
