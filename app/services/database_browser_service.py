import csv
import io
import os

from app.core.encryption import decrypt_secret
from app.core.errors import AppError
from app.drivers.database.command import run_command
from app.drivers.database.k8s import K8sConfig, run_kubectl_command
from app.models import DatabaseInstance

SUPPORTED_TYPES = {"mysql", "mariadb", "postgresql"}


class DatabaseBrowser:
    def __init__(self, instance: DatabaseInstance):
        if instance.db_type not in SUPPORTED_TYPES:
            raise AppError("DATABASE_BROWSER_UNSUPPORTED", "Database browsing is not supported for this type", 400)
        self.instance = instance
        self.password = decrypt_secret(instance.password_encrypted)

    @property
    def is_postgresql(self) -> bool:
        return self.instance.db_type == "postgresql"

    @property
    def is_k8s(self) -> bool:
        return self.instance.connection_type == "kubernetes" and bool(self.instance.k8s_config)

    def _quote(self, value: str) -> str:
        if not value or "\x00" in value:
            raise AppError("INVALID_IDENTIFIER", "Invalid database identifier", 400)
        if self.is_postgresql:
            return f'"{value.replace(chr(34), chr(34) * 2)}"'
        return f"`{value.replace('`', '``')}`"

    def _execute(self, sql: str, catalog: str | None = None) -> tuple[list[str], list[list[str | None]]]:
        env = os.environ.copy()
        if self.is_postgresql:
            env["PGPASSWORD"] = self.password
            database = catalog or self.instance.database_name or "postgres"
            connection = ["-U", self.instance.username, "-d", database]
            if not self.is_k8s:
                connection = [
                    "--host", self.instance.host, "--port", str(self.instance.port),
                    "--username", self.instance.username, "--dbname", database,
                ]
            command = ["psql", *connection, "--csv", "--command", sql]
        else:
            env["MYSQL_PWD"] = self.password
            connection = ["-u", self.instance.username] if self.is_k8s else [
                "--host", self.instance.host, "--port", str(self.instance.port), "--user", self.instance.username,
            ]
            command = ["mysql", *connection, "--batch", "--execute", sql]

        if self.is_k8s:
            result = run_kubectl_command(
                K8sConfig.from_dict(self.instance.k8s_config),
                command,
                env=env,
                timeout_seconds=30,
                output_limit=5 * 1024 * 1024,
            )
        else:
            result = run_command(command, env=env, timeout_seconds=30, output_limit=5 * 1024 * 1024)
        if not result.ok:
            raise AppError("DATABASE_QUERY_FAILED", result.stderr_tail or "Database query failed", 502)

        delimiter = "," if self.is_postgresql else "\t"
        records = list(csv.reader(io.StringIO(result.stdout_tail), delimiter=delimiter))
        if not records:
            return [], []
        columns = records[0]
        null_markers = {"\\N"} if self.is_postgresql else {"NULL"}
        rows = [[None if value in null_markers else value for value in row] for row in records[1:]]
        return columns, rows

    def list_catalogs(self) -> list[dict]:
        sql = (
            "SELECT datname AS name FROM pg_database WHERE datallowconn AND NOT datistemplate ORDER BY datname"
            if self.is_postgresql
            else "SELECT SCHEMA_NAME AS name FROM information_schema.SCHEMATA ORDER BY SCHEMA_NAME"
        )
        _, rows = self._execute(sql)
        return [{"name": row[0]} for row in rows]

    def list_tables(self, catalog: str) -> list[dict]:
        if self.is_postgresql:
            sql = (
                "SELECT table_schema, table_name, table_type FROM information_schema.tables "
                "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') ORDER BY table_schema, table_name"
            )
            _, rows = self._execute(sql, catalog)
        else:
            literal = catalog.replace("'", "''")
            sql = (
                "SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE FROM information_schema.TABLES "
                f"WHERE TABLE_SCHEMA = '{literal}' ORDER BY TABLE_NAME"
            )
            _, rows = self._execute(sql)
        return [{"schema_name": row[0], "name": row[1], "type": row[2]} for row in rows]

    def list_columns(self, catalog: str, schema: str, table: str) -> list[dict]:
        catalog_literal = catalog.replace("'", "''")
        schema_literal = schema.replace("'", "''")
        table_literal = table.replace("'", "''")
        if self.is_postgresql:
            sql = (
                "SELECT c.column_name, c.data_type, c.is_nullable, c.column_default, "
                "CASE WHEN tc.constraint_type = 'PRIMARY KEY' THEN '1' ELSE '0' END AS primary_key "
                "FROM information_schema.columns c LEFT JOIN information_schema.key_column_usage kcu "
                "ON c.table_schema=kcu.table_schema AND c.table_name=kcu.table_name "
                "AND c.column_name=kcu.column_name LEFT JOIN information_schema.table_constraints tc "
                "ON kcu.constraint_name=tc.constraint_name AND kcu.table_schema=tc.table_schema "
                f"WHERE c.table_schema='{schema_literal}' AND c.table_name='{table_literal}' "
                "ORDER BY c.ordinal_position"
            )
            _, rows = self._execute(sql, catalog)
        else:
            sql = (
                "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, "
                "CASE WHEN COLUMN_KEY='PRI' THEN '1' ELSE '0' END AS primary_key "
                "FROM information_schema.COLUMNS "
                f"WHERE TABLE_SCHEMA='{catalog_literal}' AND TABLE_NAME='{table_literal}' ORDER BY ORDINAL_POSITION"
            )
            _, rows = self._execute(sql)
        return [
            {"name": row[0], "data_type": row[1], "nullable": row[2] == "YES", "default": row[3] or None,
             "primary_key": row[4] == "1"}
            for row in rows
        ]

    def get_rows(self, catalog: str, schema: str, table: str, page: int, page_size: int) -> dict:
        table_ref = (
            f"{self._quote(schema)}.{self._quote(table)}" if self.is_postgresql
            else f"{self._quote(catalog)}.{self._quote(table)}"
        )
        _, count_rows = self._execute(f"SELECT COUNT(*) AS total FROM {table_ref}", catalog)
        total = int(count_rows[0][0]) if count_rows else 0
        offset = (page - 1) * page_size
        columns, rows = self._execute(
            f"SELECT * FROM {table_ref} LIMIT {page_size} OFFSET {offset}", catalog
        )
        return {"columns": columns, "rows": rows, "page": page, "page_size": page_size, "total": total}
