from unittest.mock import patch

from app.drivers.database.base import CommandResult
from tests.test_ownership_isolation import create_owned_database, create_user_and_headers

from .conftest import create_database_instance


def command_result(output: str) -> CommandResult:
    return CommandResult(ok=True, returncode=0, stdout_tail=output, stderr_tail="", duration_seconds=0.01)


def test_database_browser_endpoints(client, admin_headers):
    database_id = create_database_instance(client, admin_headers)
    outputs = [
        "name\ninformation_schema\norders\n",
        "TABLE_SCHEMA\tTABLE_NAME\tTABLE_TYPE\norders\tcustomers\tBASE TABLE\n",
        "COLUMN_NAME\tDATA_TYPE\tIS_NULLABLE\tCOLUMN_DEFAULT\tprimary_key\nid\tbigint\tNO\tNULL\t1\n",
        "total\n2\n",
        "id\tname\n1\tAlice\n2\tNULL\n",
    ]
    with patch("app.services.database_browser_service.run_command", side_effect=map(command_result, outputs)) as run:
        catalogs = client.get(f"/api/v1/databases/{database_id}/browser/catalogs", headers=admin_headers)
        tables = client.get(
            f"/api/v1/databases/{database_id}/browser/tables", headers=admin_headers, params={"catalog": "orders"}
        )
        columns = client.get(
            f"/api/v1/databases/{database_id}/browser/columns",
            headers=admin_headers,
            params={"catalog": "orders", "schema": "orders", "table": "customers"},
        )
        rows = client.get(
            f"/api/v1/databases/{database_id}/browser/rows",
            headers=admin_headers,
            params={"catalog": "orders", "schema": "orders", "table": "customers"},
        )

    assert catalogs.status_code == tables.status_code == columns.status_code == rows.status_code == 200
    assert catalogs.json()[-1] == {"name": "orders"}
    assert tables.json()[0]["name"] == "customers"
    assert columns.json()[0] == {
        "name": "id", "data_type": "bigint", "nullable": False, "default": None, "primary_key": True
    }
    assert rows.json()["rows"] == [["1", "Alice"], ["2", None]]
    assert "SELECT * FROM `orders`.`customers` LIMIT 20 OFFSET 0" in run.call_args_list[-1].args[0]


def test_database_browser_validates_access_and_pagination(client, admin_headers):
    database_id = create_database_instance(client, admin_headers)
    response = client.get(
        f"/api/v1/databases/{database_id}/browser/rows",
        headers=admin_headers,
        params={"catalog": "orders", "schema": "orders", "table": "customers", "page_size": 101},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PAGINATION"

    missing = client.get("/api/v1/databases/999/browser/catalogs", headers=admin_headers)
    assert missing.status_code == 404

    unauthorized = client.get(f"/api/v1/databases/{database_id}/browser/catalogs")
    assert unauthorized.status_code == 401


def test_database_browser_hides_other_users_instances(client, admin_headers):
    alice_headers = create_user_and_headers(client, admin_headers, "browser-alice")
    bob_headers = create_user_and_headers(client, admin_headers, "browser-bob")
    bob_database_id = create_owned_database(client, bob_headers, "browser-bob-db")

    response = client.get(f"/api/v1/databases/{bob_database_id}/browser/catalogs", headers=alice_headers)

    assert response.status_code == 404
