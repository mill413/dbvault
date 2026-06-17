from tests.conftest import TEST_ROOT


def create_user_and_headers(client, admin_headers, username: str, role: str = "User") -> dict:
    password = f"{username}123456"
    created = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": username, "password": password, "role": role},
    )
    assert created.status_code == 200, created.text
    login = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_owned_storage(client, headers, name: str) -> int:
    response = client.post(
        "/api/v1/storages",
        headers=headers,
        json={
            "name": name,
            "storage_type": "local",
            "config": {"root_path": str(TEST_ROOT / name)},
            "is_default": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def create_owned_database(client, headers, name: str) -> int:
    response = client.post(
        "/api/v1/databases",
        headers=headers,
        json={
            "name": name,
            "db_type": "mysql",
            "host": "127.0.0.1",
            "port": 3306,
            "username": "backup",
            "password": "database-password",
            "database_name": name,
            "environment": "test",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_non_admin_users_only_see_owned_databases_and_storages(client, admin_headers):
    alice_headers = create_user_and_headers(client, admin_headers, "alice")
    bob_headers = create_user_and_headers(client, admin_headers, "bob")

    alice_db = create_owned_database(client, alice_headers, "alice-db")
    bob_db = create_owned_database(client, bob_headers, "bob-db")
    alice_storage = create_owned_storage(client, alice_headers, "alice-storage")
    bob_storage = create_owned_storage(client, bob_headers, "bob-storage")

    alice_databases = client.get("/api/v1/databases", headers=alice_headers)
    bob_databases = client.get("/api/v1/databases", headers=bob_headers)
    admin_databases = client.get("/api/v1/databases", headers=admin_headers)
    alice_storages = client.get("/api/v1/storages", headers=alice_headers)
    bob_storages = client.get("/api/v1/storages", headers=bob_headers)
    admin_storages = client.get("/api/v1/storages", headers=admin_headers)

    assert alice_databases.json()["total"] == 1
    assert alice_databases.json()["items"][0]["id"] == alice_db
    assert bob_databases.json()["total"] == 1
    assert bob_databases.json()["items"][0]["id"] == bob_db
    assert admin_databases.json()["total"] == 2
    assert alice_storages.json()["total"] == 1
    assert alice_storages.json()["items"][0]["id"] == alice_storage
    assert bob_storages.json()["total"] == 1
    assert bob_storages.json()["items"][0]["id"] == bob_storage
    assert admin_storages.json()["total"] == 2

    assert client.get(f"/api/v1/databases/{bob_db}", headers=alice_headers).status_code == 404
    assert client.get(f"/api/v1/storages/{bob_storage}", headers=alice_headers).status_code == 404


def test_non_admin_cannot_backup_other_users_resources(client, admin_headers):
    alice_headers = create_user_and_headers(client, admin_headers, "alice")
    bob_headers = create_user_and_headers(client, admin_headers, "bob")
    alice_db = create_owned_database(client, alice_headers, "alice-db")
    alice_storage = create_owned_storage(client, alice_headers, "alice-storage")
    bob_db = create_owned_database(client, bob_headers, "bob-db")
    bob_storage = create_owned_storage(client, bob_headers, "bob-storage")

    own_upload = client.post(
        f"/api/v1/backups/upload?database_id={alice_db}&storage_id={alice_storage}&compression=none",
        headers=alice_headers,
        files={"file": ("backup.sql", b"CREATE TABLE owned(id int);", "application/sql")},
    )
    cross_database = client.post(
        f"/api/v1/backups/upload?database_id={bob_db}&storage_id={alice_storage}&compression=none",
        headers=alice_headers,
        files={"file": ("backup.sql", b"CREATE TABLE x(id int);", "application/sql")},
    )
    cross_storage = client.post(
        f"/api/v1/backups/upload?database_id={alice_db}&storage_id={bob_storage}&compression=none",
        headers=alice_headers,
        files={"file": ("backup.sql", b"CREATE TABLE x(id int);", "application/sql")},
    )
    alice_backups = client.get("/api/v1/backups", headers=alice_headers)
    bob_backups = client.get("/api/v1/backups", headers=bob_headers)
    admin_backups = client.get("/api/v1/backups", headers=admin_headers)

    assert own_upload.status_code == 200, own_upload.text
    assert cross_database.status_code == 404
    assert cross_storage.status_code == 404
    assert alice_backups.json()["total"] == 1
    assert bob_backups.json()["total"] == 0
    assert admin_backups.json()["total"] == 1


def test_kubeconfigs_are_scoped_to_creator(client, admin_headers):
    alice_headers = create_user_and_headers(client, admin_headers, "alice")
    bob_headers = create_user_and_headers(client, admin_headers, "bob")
    content = """
apiVersion: v1
kind: Config
clusters: []
contexts: []
users: []
"""

    alice_config = client.post(
        "/api/v1/kubeconfigs",
        headers=alice_headers,
        json={"name": "alice-cluster", "content": content},
    )
    bob_config = client.post(
        "/api/v1/kubeconfigs",
        headers=bob_headers,
        json={"name": "bob-cluster", "content": content},
    )
    alice_list = client.get("/api/v1/kubeconfigs", headers=alice_headers)
    bob_list = client.get("/api/v1/kubeconfigs", headers=bob_headers)
    admin_list = client.get("/api/v1/kubeconfigs", headers=admin_headers)

    assert alice_config.status_code == 200, alice_config.text
    assert bob_config.status_code == 200, bob_config.text
    assert [item["name"] for item in alice_list.json()] == ["alice-cluster"]
    assert [item["name"] for item in bob_list.json()] == ["bob-cluster"]
    assert {item["name"] for item in admin_list.json()} >= {"alice-cluster", "bob-cluster"}
    assert client.delete("/api/v1/kubeconfigs/bob-cluster", headers=alice_headers).status_code == 404
