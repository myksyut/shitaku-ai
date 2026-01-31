from fastapi.testclient import TestClient


def test_create_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/users/",
        json={"email": "test@example.com", "password": "testpassword", "full_name": "Test User"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert "id" in data


def test_create_user_duplicate_email(client: TestClient) -> None:
    # 最初のユーザー作成
    client.post(
        "/api/v1/users/",
        json={"email": "duplicate@example.com", "password": "testpassword"},
    )
    # 同じメールで再度作成
    response = client.post(
        "/api/v1/users/",
        json={"email": "duplicate@example.com", "password": "testpassword"},
    )
    assert response.status_code == 400


def test_read_users(client: TestClient) -> None:
    # ユーザー作成
    client.post(
        "/api/v1/users/",
        json={"email": "user1@example.com", "password": "testpassword"},
    )
    client.post(
        "/api/v1/users/",
        json={"email": "user2@example.com", "password": "testpassword"},
    )

    response = client.get("/api/v1/users/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_read_user(client: TestClient) -> None:
    # ユーザー作成
    create_response = client.post(
        "/api/v1/users/",
        json={"email": "read@example.com", "password": "testpassword"},
    )
    user_id = create_response.json()["id"]

    response = client.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["email"] == "read@example.com"


def test_read_user_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/users/99999")
    assert response.status_code == 404
