"""add integrity indexes and token version

Revision ID: 0006_add_integrity_indexes_and_token_version
Revises: 0005_add_job_active_backup_task
Create Date: 2026-07-03 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_add_integrity_indexes_and_token_version"
down_revision: str | None = "0005_add_job_active_backup_task"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("token_version", sa.Integer(), server_default="0", nullable=False))
    with op.batch_alter_table("backups") as batch_op:
        batch_op.create_unique_constraint("uq_backups_backup_task_id", ["backup_task_id"])
    op.create_index("ix_jobs_active_backup_task_id", "jobs", ["active_backup_task_id"], unique=False)
    op.create_index("ix_database_instances_created_by_deleted_at", "database_instances", ["created_by", "deleted_at"])
    op.create_index("ix_storages_created_by_deleted_at", "storages", ["created_by", "deleted_at"])
    op.create_index(
        "ix_backups_created_by_deleted_at_created_at",
        "backups",
        ["created_by", "deleted_at", "created_at"],
    )
    op.create_index("ix_jobs_created_by_deleted_at", "jobs", ["created_by", "deleted_at"])
    op.create_index("ix_task_events_type_task_id_id", "task_events", ["task_type", "task_id", "id"])
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.create_foreign_key(
            "fk_jobs_active_backup_task_id_backup_tasks",
            "backup_tasks",
            ["active_backup_task_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_constraint("fk_jobs_active_backup_task_id_backup_tasks", type_="foreignkey")
    op.drop_index("ix_task_events_type_task_id_id", table_name="task_events")
    op.drop_index("ix_jobs_created_by_deleted_at", table_name="jobs")
    op.drop_index("ix_backups_created_by_deleted_at_created_at", table_name="backups")
    op.drop_index("ix_storages_created_by_deleted_at", table_name="storages")
    op.drop_index("ix_database_instances_created_by_deleted_at", table_name="database_instances")
    op.drop_index("ix_jobs_active_backup_task_id", table_name="jobs")
    with op.batch_alter_table("backups") as batch_op:
        batch_op.drop_constraint("uq_backups_backup_task_id", type_="unique")
    op.drop_column("users", "token_version")
