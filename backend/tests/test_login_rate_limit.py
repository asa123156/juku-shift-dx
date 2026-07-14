"""ログインのレート制限（IP単位・アカウント単位）のテスト。"""

import pytest
from fastapi.testclient import TestClient

from services.rate_limit import (
    ACCOUNT_MAX_FAILURES,
    IP_MAX_ATTEMPTS,
    reset_login_rate_limit_for_tests,
)


@pytest.fixture()
def client():
    from main import app

    return TestClient(app)


def test_account_lockout_after_repeated_failures(client: TestClient):
    """存在しないメールでも、同一アカウントへの失敗が続けば一時ブロックされる。"""
    reset_login_rate_limit_for_tests()
    try:
        email = "rate-limit-account-test@example.com"
        for _ in range(ACCOUNT_MAX_FAILURES):
            res = client.post("/api/auth/login", json={"email": email, "password": "wrong"})
            assert res.status_code == 401

        blocked = client.post("/api/auth/login", json={"email": email, "password": "wrong"})
        assert blocked.status_code == 429
        assert "Retry-After" in blocked.headers

        # 別アカウントはロックの影響を受けない（アカウント単位のロックであることの確認）
        other_account = client.post(
            "/api/auth/login", json={"email": "teacher@example.com", "password": "demo"}
        )
        assert other_account.status_code == 200
    finally:
        reset_login_rate_limit_for_tests()


def test_successful_login_resets_account_failures(client: TestClient):
    reset_login_rate_limit_for_tests()
    try:
        email = "teacher@example.com"
        for _ in range(ACCOUNT_MAX_FAILURES - 1):
            res = client.post("/api/auth/login", json={"email": email, "password": "wrong"})
            assert res.status_code == 401

        ok = client.post("/api/auth/login", json={"email": email, "password": "demo"})
        assert ok.status_code == 200

        # 成功でカウンタがリセットされるので、続けて失敗してもすぐにはブロックされない
        again = client.post("/api/auth/login", json={"email": email, "password": "wrong"})
        assert again.status_code == 401
    finally:
        reset_login_rate_limit_for_tests()


def test_ip_lockout_after_too_many_attempts(client: TestClient):
    """IP単位: 異なるメール宛でも、同一IPからの試行数が多ければブロックされる。"""
    reset_login_rate_limit_for_tests()
    try:
        for i in range(IP_MAX_ATTEMPTS):
            res = client.post(
                "/api/auth/login",
                json={"email": f"ip-test-{i}@example.com", "password": "wrong"},
            )
            assert res.status_code == 401

        blocked = client.post(
            "/api/auth/login",
            json={"email": "ip-test-overflow@example.com", "password": "wrong"},
        )
        assert blocked.status_code == 429
    finally:
        reset_login_rate_limit_for_tests()
