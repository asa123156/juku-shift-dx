"""POST /api/auth/change-password のテスト。"""

import json

import pytest
from fastapi.testclient import TestClient

from config import DATA_DIR

USERS_PATH = DATA_DIR / "users.json"


@pytest.fixture()
def client():
    from main import app

    return TestClient(app)


@pytest.fixture()
def restore_users():
    """テスト後に users.json を元に戻す。"""
    original = USERS_PATH.read_text(encoding="utf-8")
    yield
    USERS_PATH.write_text(original, encoding="utf-8")


def _login(client: TestClient, email: str, password: str):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_change_password_success_and_relogin(client: TestClient, restore_users):
    login = _login(client, "teacher@example.com", "demo")
    assert login.status_code == 200
    token = login.json()["token"]

    res = client.post(
        "/api/auth/change-password",
        json={"current_password": "demo", "new_password": "new-pass-123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text

    assert _login(client, "teacher@example.com", "demo").status_code == 401
    assert _login(client, "teacher@example.com", "new-pass-123").status_code == 200

    # ハッシュのまま保存されている（平文が書かれていない）こと
    users = json.loads(USERS_PATH.read_text(encoding="utf-8"))
    me = next(u for u in users if u["email"] == "teacher@example.com")
    assert me["password"].startswith("$2")


def test_change_password_wrong_current(client: TestClient, restore_users):
    token = _login(client, "student@example.com", "demo").json()["token"]
    res = client.post(
        "/api/auth/change-password",
        json={"current_password": "wrong", "new_password": "new-pass-123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_change_password_too_short(client: TestClient, restore_users):
    token = _login(client, "student@example.com", "demo").json()["token"]
    res = client.post(
        "/api/auth/change-password",
        json={"current_password": "demo", "new_password": "short"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


def test_change_password_requires_auth(client: TestClient):
    res = client.post(
        "/api/auth/change-password",
        json={"current_password": "demo", "new_password": "new-pass-123"},
    )
    assert res.status_code == 401
