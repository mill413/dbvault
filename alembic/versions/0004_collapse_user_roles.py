"""collapse user roles

Revision ID: 0004_collapse_user_roles
Revises: 0003_add_k8s_connection
Create Date: 2026-06-17 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_collapse_user_roles"
down_revision: str | None = "0003_add_k8s_connection"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    users = sa.table("users", sa.column("role", sa.String()))
    op.execute(users.update().where(users.c.role.in_(("Operator", "Viewer"))).values(role="User"))


def downgrade() -> None:
    users = sa.table("users", sa.column("role", sa.String()))
    op.execute(users.update().where(users.c.role == "User").values(role="Operator"))
