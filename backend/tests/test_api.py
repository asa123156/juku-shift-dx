"""API スモークテスト。実行: cd backend && python -m tests.test_api"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SUBMISSIONS = DATA_DIR / "teacher-submissions.json"
OVERRIDES = DATA_DIR / "admin-overrides.json"
ASSIGNMENTS = DATA_DIR / "assignments.json"


def _reset_data() -> None:
    SUBMISSIONS.write_text("{}", encoding="utf-8")
    OVERRIDES.write_text("{}", encoding="utf-8")
    ASSIGNMENTS.write_text("{}", encoding="utf-8")


def run_tests() -> None:
    _reset_data()
    from main import app

    client = TestClient(app)

    assert client.get("/health").json()["status"] == "ok"

    dates = client.get("/api/shifts/dates").json()
    assert "2026-06-10" in dates["dates"]

    dash = client.get("/api/shifts", params={"date": "2026-06-11"}).json()
    assert dash["date"] == "2026-06-11"
    assert len(dash["teachers"]) == 3

    login = client.post(
        "/api/auth/login",
        json={"email": "teacher@example.com", "password": "demo"},
    )
    assert login.status_code == 200
    assert login.json()["role"] == "teacher"
    assert login.json()["teacher_id"] == 1

    assert client.post("/api/auth/login", json={"email": "x@y.com", "password": "bad"}).status_code == 401

    payload = {
        "teacher_id": 1,
        "date": "2026-06-10",
        "slots": {"1": "available", "2": "available", "3": "unavailable", "4": "blank"},
    }
    assert client.post("/api/shifts", json=payload).status_code == 200

    merged = client.get("/api/shifts", params={"date": "2026-06-10"}).json()
    t1 = next(t for t in merged["teachers"] if t["id"] == 1)
    assert t1["s1"] == "待機"

    admin = client.patch(
        "/api/admin/shifts/slot",
        json={"date": "2026-06-10", "teacher_id": 1, "slot": 1, "status": "確定"},
    )
    assert admin.status_code == 200
    assert admin.json()["teachers"][0]["s1"] == "確定"

    confirm = client.post("/api/admin/shifts/confirm", json={"date": "2026-06-11"})
    assert confirm.status_code == 200
    assert confirm.json()["confirmed_slots"] >= 0

    lessons = client.get("/api/lessons").json()
    assert len(lessons) >= 1

    assert client.get("/api/shifts", params={"date": "1999-01-01"}).status_code == 404

    candidates = client.post(
        "/api/admin/assignments/candidates",
        json={"date": "2026-06-10", "student_id": 1, "subject": "数学I"},
    )
    assert candidates.status_code == 200
    assert isinstance(candidates.json()["candidates"], list)

    auto = client.post("/api/admin/auto-assign", json={"date": "2026-06-10"})
    assert auto.status_code == 200
    body = auto.json()
    assert "proposals" in body
    if body["proposals"]:
        dash = body["dashboard"]
        statuses = [t["s1"] for t in dash["teachers"]] + [t["s2"] for t in dash["teachers"]]
        assert "AI提案" in statuses or len(body["proposals"]) == 0

    print("All tests passed.")


if __name__ == "__main__":
    run_tests()
