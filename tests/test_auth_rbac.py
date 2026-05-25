from tests.conftest import create_database_instance, create_local_storage


def test_initial_admin_can_login_and_read_me(client, admin_headers):
    response = client.get("/api/v1/auth/me", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert response.json()["role"] == "Admin"


def test_viewer_cannot_run_backup(client, admin_headers):
    response = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": "viewer",
            "password": "viewer123456789",
            "role": "Viewer",
        },
    )
    assert response.status_code == 200, response.text

    login = client.post(
        "/api/v1/auth/login",
        json={"username": "viewer", "password": "viewer123456789"},
    )
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    database_id = create_database_instance(client, admin_headers)
    storage_id = create_local_storage(client, admin_headers)

    forbidden = client.post(
        "/api/v1/backups/run",
        headers=viewer_headers,
        json={"database_id": database_id, "storage_id": storage_id},
    )

    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"

