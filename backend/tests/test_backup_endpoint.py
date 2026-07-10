"""POST /api/admin/backup のテスト。"""

import shutil

import pytest
from fastapi.testclient import TestClient

from scripts.backup_data import BACKUPS_DIR
from security import create_access_token


@pytest.fixture()
def client():
    from main import app

    return TestClient(app)


def _auth_header(role: str) -> dict[str, str]:
    token = create_access_token(
        {
            "sub": f"{role}@example.com",
            "role": role,
            "teacher_id": 1 if role == "teacher" else None,
            "student_id": None,
            "name": role,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_backup_creates_snapshot(client: TestClient):
    res = client.post("/api/admin/backup", headers=_auth_header("admin"))
    assert res.status_code == 200, res.text
    snapshot = res.json()["snapshot"]
    snapshot_dir = BACKUPS_DIR / snapshot
    try:
        assert snapshot_dir.is_dir()
        assert (snapshot_dir / "juku_shift.db").is_file()
        assert (snapshot_dir / "data" / "users.json").is_file()
    finally:
        shutil.rmtree(snapshot_dir, ignore_errors=True)


def test_backup_requires_admin(client: TestClient):
    res = client.post("/api/admin/backup", headers=_auth_header("teacher"))
    assert res.status_code == 403
    res_anon = client.post("/api/admin/backup")
    assert res_anon.status_code == 401
