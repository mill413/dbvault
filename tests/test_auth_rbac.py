def test_initial_admin_can_login_and_read_me(client, admin_headers):
    response = client.get("/api/v1/auth/me", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert response.json()["role"] == "Admin"


def test_legacy_roles_are_rejected(client, admin_headers):
    response = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": "viewer",
            "password": "viewer123456789",
            "role": "Viewer",
        },
    )
    assert response.status_code == 422

    response = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": "operator",
            "password": "operator123456",
            "role": "Operator",
        },
    )
    assert response.status_code == 422
