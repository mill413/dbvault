"""add job active backup task slot

Revision ID: 0005_add_job_active_backup_task
Revises: 0004_collapse_user_roles
Create Date: 2026-07-03 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_add_job_active_backup_task"
down_revision: str | None = "0004_collapse_user_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("active_backup_task_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "active_backup_task_id")
