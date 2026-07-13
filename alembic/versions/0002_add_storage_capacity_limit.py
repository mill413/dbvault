"""add storage capacity limit

Revision ID: 0002_add_storage_capacity_limit
Revises: 0001_initial_schema
Create Date: 2026-05-31 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_add_storage_capacity_limit"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "storages",
        sa.Column("capacity_limit_bytes", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("storages", "capacity_limit_bytes")
