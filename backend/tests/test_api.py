"""API スモークテスト。実行: cd backend && python -m tests.test_api"""

from fastapi.testclient import TestClient


def _reset_data() -> None:
    from services.admin_store import reset_admin_overrides_for_tests
    from services.assignment_store import reset_assignments_for_tests
    from services.dashboard_store import reset_shift_dashboards_for_tests
    from services.period_store import reset_periods_for_tests
    from services.submission_store import reset_submissions_for_tests

    reset_periods_for_tests()
    reset_submissions_for_tests()
    reset_admin_overrides_for_tests()
    reset_assignments_for_tests()
    reset_shift_dashboards_for_tests()


def run_tests() -> None:
    from main import app

    _reset_data()
    client = TestClient(app)

    assert client.get("/health").json()["status"] == "ok"

    dates = client.get("/api/shifts/dates").json()
    assert "2026-06-10" in dates["dates"]

    dash = client.get("/api/shifts", params={"date": "2026-06-11"}).json()
    assert dash["date"] == "2026-06-11"
    assert len(dash["teachers"]) == 3
    assert len(dash.get("time_slots", [])) == 4
    assert dash["time_slots"][0]["start"] == "13:30"

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
        "slots": {"1": "", "2": "", "3": "×", "4": ""},
    }
    assert client.post("/api/shifts", json=payload).status_code == 200

    me = client.get("/api/shifts/me", params={"teacher_id": 1, "date": "2026-06-10"}).json()
    assert me["slots"]["3"] == "×"

    schedule = client.get(
        "/api/shifts/my-schedule",
        params={"role": "teacher", "entity_id": 1, "period_id": 1},
    ).json()
    assert schedule["period_status"] == "COLLECTING"
    assert len(schedule["dates"]) == 3
    assert len(schedule.get("time_slots", [])) == 4

    bulk = client.patch(
        "/api/shifts/bulk",
        json={
            "role": "student",
            "entity_id": 1,
            "period_id": 1,
            "submissions": [
                {"date": "2026-06-10", "slots": {"1": "", "2": "", "3": "×", "4": ""}},
                {"date": "2026-06-11", "slots": {"1": "×", "2": "", "3": "", "4": ""}},
            ],
        },
    )
    assert bulk.status_code == 200
    assert len(bulk.json()["saved_dates"]) == 2

    student_login = client.post(
        "/api/auth/login",
        json={"email": "student@example.com", "password": "demo"},
    )
    assert student_login.status_code == 200
    assert student_login.json()["role"] == "student"

    periods = client.get("/api/admin/periods").json()
    assert len(periods["periods"]) >= 1

    merged = client.get("/api/shifts", params={"date": "2026-06-10"}).json()
    t1 = next(t for t in merged["teachers"] if t["id"] == 1)
    assert t1["s3"] == "×"
    assert t1["s2"] == ""

    grid = client.get("/api/admin/assignments/grid", params={"date": "2026-06-10"}).json()
    assert len(grid["teachers"]) == 3
    assert "time_slots" in grid

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
    assert "grid" in body

    finalize = client.patch("/api/admin/periods/1/status", json={"status": "FINALIZED"})
    assert finalize.status_code == 200

    finalized_dash = client.get("/api/shifts", params={"date": "2026-06-10"}).json()
    t1f = next(t for t in finalized_dash["teachers"] if t["id"] == 1)
    assert t1f["s1"] == "◎"

    student_schedule = client.get(
        "/api/shifts/my-schedule",
        params={"role": "student", "entity_id": 1, "period_id": 1},
    ).json()
    assert student_schedule["readonly"] is True
    assert student_schedule.get("message")

    lessons = client.get("/api/lessons").json()
    assert len(lessons) >= 1

    assert client.get("/api/shifts", params={"date": "1999-01-01"}).status_code == 404

    csv_body = (
        "date,student_id,student_name,subject\n"
        "2026-06-11,99,テスト太郎,英語\n"
    )
    imported = client.post(
        "/api/admin/assignment-requests/import",
        files={"file": ("requests.csv", csv_body.encode("utf-8"), "text/csv")},
    )
    assert imported.status_code == 200
    imp = imported.json()
    assert imp["imported_count"] + imp["skipped_count"] == 1

    print("All tests passed.")


if __name__ == "__main__":
    run_tests()
