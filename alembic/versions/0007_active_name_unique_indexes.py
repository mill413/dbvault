"""use active-row unique indexes for soft-deleted names

Revision ID: 0007_active_name_unique_indexes
Revises: 0006_add_integrity_indexes_and_token_version
Create Date: 2026-07-03 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_active_name_unique_indexes"
down_revision: str | None = "0006_add_integrity_indexes_and_token_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NAMING_CONVENTION = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def _drop_global_unique(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        constraint_name = f"{table_name}_{column_name}_key"
        existing_names = {constraint["name"] for constraint in sa.inspect(bind).get_unique_constraints(table_name)}
        if constraint_name in existing_names:
            op.drop_constraint(constraint_name, table_name, type_="unique")
        return
    constraint_name = f"uq_{table_name}_{column_name}"
    with op.batch_alter_table(table_name, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_constraint(constraint_name, type_="unique")


def _create_global_unique(table_name: str, column_name: str) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.create_unique_constraint(f"uq_{table_name}_{column_name}", [column_name])


def _create_active_unique_index(table_name: str, column_name: str, index_name: str) -> None:
    op.create_index(
        index_name,
        table_name,
        [column_name],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )


def _rename_deleted_duplicates(table_name: str, column_name: str, max_length: int) -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            f"SELECT id, {column_name} AS value, deleted_at FROM {table_name} "
            "ORDER BY CASE WHEN deleted_at IS NULL THEN 0 ELSE 1 END, id"
        )
    ).mappings()
    seen = set()
    for row in rows:
        value = row["value"]
        if value not in seen:
            seen.add(value)
            continue
        suffix = f"-deleted-{row['id']}"
        prefix = value[: max_length - len(suffix)]
        replacement = f"{prefix}{suffix}"
        connection.execute(
            sa.text(f"UPDATE {table_name} SET {column_name} = :replacement WHERE id = :id"),
            {"replacement": replacement, "id": row["id"]},
        )
        seen.add(replacement)


def upgrade() -> None:
    _drop_global_unique("users", "username")
    _drop_global_unique("database_instances", "name")
    _drop_global_unique("storages", "name")
    _create_active_unique_index("users", "username", "uq_users_username_active")
    _create_active_unique_index("database_instances", "name", "uq_database_instances_name_active")
    _create_active_unique_index("storages", "name", "uq_storages_name_active")


def downgrade() -> None:
    op.drop_index("uq_storages_name_active", table_name="storages")
    op.drop_index("uq_database_instances_name_active", table_name="database_instances")
    op.drop_index("uq_users_username_active", table_name="users")
    _rename_deleted_duplicates("storages", "name", 128)
    _rename_deleted_duplicates("database_instances", "name", 128)
    _rename_deleted_duplicates("users", "username", 64)
    _create_global_unique("storages", "name")
    _create_global_unique("database_instances", "name")
    _create_global_unique("users", "username")
