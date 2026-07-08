"""API スモークテスト。実行: cd backend && python -m tests.test_api"""

from fastapi.testclient import TestClient

from services.slot_timing import SLOT_COUNT, empty_slot_map


def _empty_slots(**overrides: str) -> dict[str, str]:
    slots = empty_slot_map()
    slots.update({str(k): v for k, v in overrides.items()})
    return slots


def _student_slots(**overrides: str) -> dict[str, str]:
    """生徒提出: 未指定コマは × で埋める。"""
    slots = {str(i): "×" for i in range(1, SLOT_COUNT + 1)}
    slots.update({str(k): v for k, v in overrides.items()})
    return slots


def _reset_data() -> None:
    from scripts.generate_demo_data import main as generate_demo
    from scripts.reset_demo import reset_submissions_from_json
    from services.admin_store import reset_admin_overrides_for_tests
    from services.assignment_store import reset_assignments_from_json
    from services.dashboard_store import reset_shift_dashboards_for_tests
    from services.entity_store import reset_entities_for_tests
    from services.period_store import reset_periods_for_tests

    from services.schedule_workbook_store import reset_period_workbooks_for_tests

    generate_demo()
    reset_periods_for_tests()
    reset_entities_for_tests()
    reset_period_workbooks_for_tests()
    reset_shift_dashboards_for_tests()
    reset_submissions_from_json()
    reset_admin_overrides_for_tests()
    reset_assignments_from_json()
    _reset_publish_and_change_requests()
    from services.student_plan_store import reset_student_plans_for_tests

    reset_student_plans_for_tests()


def _reset_publish_and_change_requests() -> None:
    from database import Base, engine
    import models  # noqa: F401
    from models import (
        ShiftChangeRequest,
        StudentSchedulePublish,
        StudentScheduleRequestPublish,
        TeacherSchedulePublish,
    )
    from sqlalchemy.orm import Session
    from database import SessionLocal

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        db.query(ShiftChangeRequest).delete()
        db.query(StudentSchedulePublish).delete()
        db.query(StudentScheduleRequestPublish).delete()
        db.query(TeacherSchedulePublish).delete()
        db.commit()


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
    assert len(dash.get("time_slots", [])) == SLOT_COUNT
    assert dash["time_slots"][0]["start"] == "13:00"

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
        "slots": _empty_slots(**{"3": "×"}),
    }
    assert client.post("/api/shifts", json=payload).status_code == 200

    me = client.get("/api/shifts/me", params={"teacher_id": 1, "date": "2026-06-10"}).json()
    assert me["slots"]["3"] == "×"

    schedule = client.get(
        "/api/shifts/my-schedule",
        params={"role": "teacher", "entity_id": 1, "period_id": 1},
    ).json()
    assert schedule["period_status"] == "COLLECTING"
    assert len(schedule["dates"]) == 11  # 6/9〜6/20、日曜除外
    assert len(schedule.get("time_slots", [])) == SLOT_COUNT

    bulk = client.patch(
        "/api/shifts/bulk",
        json={
            "role": "student",
            "entity_id": 1,
            "period_id": 1,
            "submissions": [
                {
                    "date": "2026-06-10",
                    "slots": _student_slots(**{
                        "1": "",
                        "2": "◎",
                        "3": "×",
                    }),
                },
                {
                    "date": "2026-06-11",
                    "slots": _student_slots(**{
                        "1": "×",
                        "2": "",
                    }),
                },
            ],
        },
    )
    assert bulk.status_code == 200
    assert len(bulk.json()["saved_dates"]) == 2

    after_submit = client.get(
        "/api/shifts/my-schedule",
        params={"role": "student", "entity_id": 1, "period_id": 1},
    ).json()
    june10 = next(d for d in after_submit["dates"] if d["date"] == "2026-06-10")
    assert june10["slots"]["2"] == "◎"

    request_publish = client.post(
        "/api/admin/assignments/publish-request",
        json={"period_id": 1, "student_id": 1},
    )
    assert request_publish.status_code == 200, request_publish.text

    student_login = client.post(
        "/api/auth/login",
        json={"email": "student@example.com", "password": "demo"},
    )
    assert student_login.status_code == 200
    assert student_login.json()["role"] == "student"

    student_schedule = client.get(
        "/api/shifts/my-schedule",
        params={"role": "student", "entity_id": 1, "period_id": 1},
    ).json()
    assert student_schedule["period_status"] == "COLLECTING"
    assert student_schedule["readonly"] is False
    assert student_schedule.get("message")
    day_june10 = next(d for d in student_schedule["dates"] if d["date"] == "2026-06-10")
    assert day_june10["slots"]["1"] == "◎"
    assert day_june10["locked_slots"]["1"] is True
    assert day_june10["slots"]["3"] == "×"

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

    sheets = client.get("/api/admin/assignments/sheets", params={"period_id": 1}).json()
    assert len(sheets["dates"]) == 11
    assert len(sheets["students"]) >= 5
    assert sheets["pending_total"] > 0

    auto_period = client.post(
        "/api/admin/auto-assign-period",
        json={
            "period_id": 1,
            "rules": {
                "no_teacher_gaps": True,
                "weekly_limits": {"国語": 1, "数学": 2, "英語": 0},
            },
        },
    )
    assert auto_period.status_code == 200
    assert auto_period.json()["assigned_count"] > 0

    sheets_after = client.get("/api/admin/assignments/sheets", params={"period_id": 1}).json()
    blocked = client.post(
        "/api/admin/assignments/publish-schedule",
        json={"period_id": 1, "student_id": 1},
    )
    assert blocked.status_code == 409

    ready_student = next(s for s in sheets_after["students"] if s["pending_count"] == 0)
    ready_request = client.post(
        "/api/admin/assignments/publish-request",
        json={"period_id": 1, "student_id": ready_student["id"]},
    )
    assert ready_request.status_code == 200, ready_request.text
    publish = client.post(
        "/api/admin/assignments/publish-schedule",
        json={"period_id": 1, "student_id": ready_student["id"]},
    )
    assert publish.status_code == 200

    teacher_row = sheets_after["teachers"][0]
    teacher_request = client.post(
        "/api/admin/assignments/publish-teacher-request",
        json={"period_id": 1, "teacher_id": teacher_row["id"]},
    )
    assert teacher_request.status_code == 200, teacher_request.text
    publish_teacher = client.post(
        "/api/admin/assignments/publish-teacher-schedule",
        json={"period_id": 1, "teacher_id": teacher_row["id"]},
    )
    assert publish_teacher.status_code == 200, publish_teacher.text
    assert publish_teacher.json()["already_published"] is False

    published_schedule = client.get(
        "/api/shifts/my-schedule",
        params={"role": "student", "entity_id": ready_student["id"], "period_id": 1},
    ).json()
    assert published_schedule["readonly"] is True
    assert published_schedule.get("schedule_published") is True
    assert "確定" in (published_schedule.get("message") or "")

    publish_all = client.post("/api/admin/assignments/publish-all", json={"period_id": 1})
    assert publish_all.status_code == 200, publish_all.text
    assert publish_all.json()["teachers_published"] >= 1

    teacher_schedule = client.get(
        "/api/shifts/my-schedule",
        params={"role": "teacher", "entity_id": 1, "period_id": 1},
    ).json()
    assert teacher_schedule.get("schedule_published") is True

    pub_day = next(d for d in published_schedule["dates"] if d["date"] == "2026-06-10")
    change_slot = None
    for sk in map(str, range(1, SLOT_COUNT + 1)):
        if pub_day["locked_slots"].get(sk):
            continue
        if pub_day["slots"].get(sk, "") != "×":
            change_slot = int(sk)
            break
    assert change_slot is not None, "editable slot for change request"

    change_req = client.post(
        "/api/shifts/change-requests",
        json={
            "period_id": 1,
            "role": "student",
            "entity_id": ready_student["id"],
            "date": "2026-06-10",
            "slot": change_slot,
            "requested_symbol": "×",
            "reason": "テスト",
        },
    )
    assert change_req.status_code == 200, change_req.text

    pending = client.get("/api/admin/change-requests", params={"period_id": 1, "status": "PENDING"})
    assert pending.status_code == 200
    assert pending.json()["pending_count"] >= 1
    req_id = pending.json()["requests"][0]["id"]
    approved = client.patch(f"/api/admin/change-requests/{req_id}", json={"action": "approve"})
    assert approved.status_code == 200

    from tests.test_juku_grid import _build_minimal_grid_xlsx

    grid_xlsx = _build_minimal_grid_xlsx()
    grid_import = client.post(
        "/api/import/juku-grid",
        params={"period_id": 1},
        files={"file": ("grid.xlsx", grid_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert grid_import.status_code == 200, grid_import.text
    assert grid_import.json()["rows_processed"] == 1
    assert grid_import.json()["imported_sheet_count"] == 1

    schedule_csv = (
        "講師名,氏名,学年,科目,種別,日付,コマ\n"
        "CSV新規講師,CSV生徒太郎,中2,数学,通常授業,2026-06-11,1\n"
        "CSV新規講師,CSV生徒花子,小5,国語,講習,2026-06-11,2\n"
    )
    schedule_import = client.post(
        "/api/import/schedule",
        params={"period_id": 1},
        files={"file": ("schedule.csv", schedule_csv.encode("utf-8-sig"), "text/csv")},
    )
    assert schedule_import.status_code == 200, schedule_import.text
    imp_schedule = schedule_import.json()
    assert imp_schedule["rows_processed"] == 2
    assert imp_schedule["teachers_created"] == 1
    assert imp_schedule["students_created"] == 2
    assert imp_schedule["regular_slots"] == 1
    assert imp_schedule["blank_slots"] == 1

    teachers_after = client.get("/api/admin/teachers").json()["teachers"]
    csv_teacher = next(t for t in teachers_after if t["name"] == "CSV新規講師")
    from services.period_store import get_entity_base_day

    teacher_base = get_entity_base_day(1, "teacher", csv_teacher["id"], "2026-06-11")
    assert teacher_base["1"] == "◎"
    assert teacher_base["2"] == ""

    finalize = client.patch("/api/admin/periods/1/status", json={"status": "FINALIZED", "force": True})
    assert finalize.status_code == 200, finalize.text

    export_resp = client.get(
        "/api/export/juku-schedule",
        params={"period_id": 1},
    )
    assert export_resp.status_code == 200, export_resp.text
    assert export_resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(export_resp.content) > 1000

    missing_workbook = client.get("/api/export/juku-schedule", params={"period_id": 99})
    assert missing_workbook.status_code == 404

    google_status = client.get("/api/google/status")
    assert google_status.status_code == 200
    assert "configured" in google_status.json()

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

    created = client.post(
        "/api/admin/students",
        json={"name": "テスト花子", "school_level": "middle", "grade_year": 1},
    )
    assert created.status_code == 200
    new_id = created.json()["id"]
    assert created.json()["grade_label"] == "中1"

    updated = client.patch(
        f"/api/admin/students/{new_id}",
        json={"name": "テスト花子改", "school_level": "high", "grade_year": 2},
    )
    assert updated.status_code == 200
    assert updated.json()["grade_label"] == "高2"

    deleted = client.delete(f"/api/admin/students/{new_id}")
    assert deleted.status_code == 200

    t_created = client.post("/api/admin/teachers", json={"name": "仮講師"})
    assert t_created.status_code == 200
    t_id = t_created.json()["id"]

    t_updated = client.patch(f"/api/admin/teachers/{t_id}", json={"name": "仮講師改"})
    assert t_updated.status_code == 200
    assert t_updated.json()["name"] == "仮講師改"

    t_deleted = client.delete(f"/api/admin/teachers/{t_id}")
    assert t_deleted.status_code == 200

    new_period = client.post(
        "/api/admin/periods",
        json={
            "name": "削除復元テスト講習",
            "start_date": "2026-07-01",
            "end_date": "2026-07-05",
            "closed_dates": [],
        },
    )
    assert new_period.status_code == 200, new_period.text
    new_period_id = new_period.json()["period"]["id"]

    request_from_draft = client.post(
        "/api/admin/assignments/publish-request",
        json={"period_id": new_period_id, "student_id": 1},
    )
    assert request_from_draft.status_code == 200, request_from_draft.text
    periods_now = client.get("/api/admin/periods").json()["periods"]
    draft_promoted = next(p for p in periods_now if p["id"] == new_period_id)
    assert draft_promoted["status"] == "COLLECTING"

    deleted = client.delete(f"/api/admin/periods/{new_period_id}")
    assert deleted.status_code == 200, deleted.text

    periods_after_delete = client.get("/api/admin/periods").json()
    assert all(p["id"] != new_period_id for p in periods_after_delete["periods"])
    deleted_periods = client.get("/api/admin/periods/deleted").json()
    assert any(p["id"] == new_period_id for p in deleted_periods["periods"])

    restored = client.patch(f"/api/admin/periods/{new_period_id}/restore")
    assert restored.status_code == 200, restored.text
    periods_after_restore = client.get("/api/admin/periods").json()
    assert any(p["id"] == new_period_id for p in periods_after_restore["periods"])

    print("All tests passed.")


if __name__ == "__main__":
    run_tests()
