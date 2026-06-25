"""add k8s connection support

Revision ID: 0003_add_k8s_connection
Revises: 0002_add_storage_capacity_limit
Create Date: 2026-05-31 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_add_k8s_connection"
down_revision: str | None = "0002_add_storage_capacity_limit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "database_instances",
        sa.Column("connection_type", sa.String(32), nullable=False, server_default="direct"),
    )
    op.add_column(
        "database_instances",
        sa.Column("k8s_config", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("database_instances", "k8s_config")
    op.drop_column("database_instances", "connection_type")
