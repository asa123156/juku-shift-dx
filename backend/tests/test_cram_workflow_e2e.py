"""講習フロー E2E: 10 回連続で全機能を通す。

流れ:
  講習作成 → 希望割り当て → 通常授業入力 → 提案書送付 →
  スケジュール入力 → 割り当て → 確定提出
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from services.slot_timing import SLOT_COUNT, empty_slot_map

RUN_COUNT = 10


def _empty_teacher_slots(**overrides: str) -> dict[str, str]:
    slots = empty_slot_map()
    slots.update({str(k): v for k, v in overrides.items()})
    return slots


def _student_slots(**overrides: str) -> dict[str, str]:
    slots = {str(i): "×" for i in range(1, SLOT_COUNT + 1)}
    slots.update({str(k): v for k, v in overrides.items()})
    return slots


def _reset_workflow_state() -> None:
    from database import Base, SessionLocal, engine
    import models  # noqa: F401
    from models import (
        ShiftChangeRequest,
        StudentSchedulePublish,
        StudentScheduleRequestPublish,
        TeacherSchedulePublish,
        TeacherScheduleRequestPublish,
    )
    from services.class_schedule_store import reset_class_schedules_for_tests
    from services.student_plan_store import reset_student_plans_for_tests
    from services.submission_store import reset_submissions_for_tests

    Base.metadata.create_all(bind=engine)
    reset_class_schedules_for_tests()
    reset_submissions_for_tests()
    reset_student_plans_for_tests()
    with SessionLocal() as db:
        db.query(ShiftChangeRequest).delete()
        db.query(StudentSchedulePublish).delete()
        db.query(StudentScheduleRequestPublish).delete()
        db.query(TeacherSchedulePublish).delete()
        db.query(TeacherScheduleRequestPublish).delete()
        db.commit()


def _fail(step: str, response, failures: list[str], run_index: int) -> None:
    detail = response.text[:500] if hasattr(response, "text") else str(response)
    failures.append(f"[試行 {run_index + 1}] {step}: HTTP {response.status_code} — {detail}")


def _run_single_workflow(client: TestClient, run_index: int, failures: list[str]) -> None:
    _reset_workflow_state()

    from scripts.generate_demo_data import main as generate_demo
    from services.entity_store import reset_entities_for_tests
    from services.period_store import reset_periods_for_tests

    generate_demo()
    reset_periods_for_tests()
    reset_entities_for_tests()

    start = date(2026, 6, 9) + timedelta(days=14 * run_index)
    end = start + timedelta(days=10)
    period_name = f"E2E講習{run_index + 1}"

    # 1. 講習作成
    created = client.post(
        "/api/admin/periods",
        json={
            "name": period_name,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "closed_dates": [],
            "location_slug": "hakutei",
        },
    )
    if created.status_code != 200:
        _fail("講習作成", created, failures, run_index)
        return
    period = created.json()["period"]
    period_id = period["id"]
    open_dates = created.json()["open_dates"]
    if not open_dates:
        failures.append(f"[試行 {run_index + 1}] 講習作成: 開校日が 0 件")
        return

    activated = client.patch(f"/api/admin/periods/{period_id}/activate")
    if activated.status_code != 200:
        _fail("講習 activate", activated, failures, run_index)
        return

    collecting = client.patch(
        f"/api/admin/periods/{period_id}/status",
        json={"status": "COLLECTING"},
    )
    if collecting.status_code != 200:
        _fail("講習 COLLECTING", collecting, failures, run_index)
        return

    dashboard = client.get("/api/admin/dashboard/summary", params={"period_id": period_id})
    if dashboard.status_code != 200:
        _fail("ダッシュボード", dashboard, failures, run_index)

    students = client.get("/api/admin/students").json().get("students", [])
    teachers = client.get("/api/admin/teachers").json().get("teachers", [])
    if not students or not teachers:
        failures.append(f"[試行 {run_index + 1}] マスタ: 生徒または講師が空")
        return

    anchor_date = open_dates[0]
    teacher_id = teachers[0]["id"]
    student = students[0]

    # 2. 希望割り当て（教科・コマ数）
    for sid in [s["id"] for s in students[:3]]:
        plans = client.put(
            f"/api/admin/periods/{period_id}/students/{sid}/plans",
            json={
                "plans": [
                    {"subject": "数学", "slot_count": 1},
                    {"subject": "英語", "slot_count": 1},
                ],
            },
        )
        if plans.status_code != 200:
            _fail(f"希望割当 student={sid}", plans, failures, run_index)
            return

    sheets_plans = client.get("/api/admin/assignments/sheets", params={"period_id": period_id})
    if sheets_plans.status_code != 200:
        _fail("割当シート（希望後）", sheets_plans, failures, run_index)
    elif sheets_plans.json().get("pending_total", 0) <= 0:
        failures.append(f"[試行 {run_index + 1}] 希望割当: pending_total が 0（期待 > 0）")

    # 3. 通常授業入力（時間割表・固定枠）
    grid_ctx = client.get("/api/calendar/grid-context", params={"date": anchor_date})
    if grid_ctx.status_code != 200:
        _fail("grid-context", grid_ctx, failures, run_index)

    fixed = client.post(
        "/api/admin/assignments/manual",
        json={
            "date": anchor_date,
            "student_name": student["name"],
            "subject": "数学",
            "teacher_id": teacher_id,
            "slot": 2,
            "period_id": period_id,
            "skip_rules": True,
            "is_fixed": True,
        },
    )
    if fixed.status_code != 200:
        _fail("通常授業入力", fixed, failures, run_index)
        return

    capacity = client.patch(
        "/api/admin/assignments/grid/capacity",
        json={"date": anchor_date, "teacher_id": teacher_id, "slot": 3, "max_lanes": 4},
    )
    if capacity.status_code != 200:
        _fail("授業形態 1対4", capacity, failures, run_index)

    # 4. 提案書送付（生徒・講師）
    for s in students:
        if s.get("schedule_requested"):
            continue
        r = client.post(
            "/api/admin/assignments/publish-request",
            json={"period_id": period_id, "student_id": s["id"]},
        )
        if r.status_code != 200:
            _fail(f"提案書送付 student={s['id']}", r, failures, run_index)
            return

    for t in teachers:
        r = client.post(
            "/api/admin/assignments/publish-teacher-request",
            json={"period_id": period_id, "teacher_id": t["id"]},
        )
        if r.status_code != 200:
            _fail(f"提案書送付 teacher={t['id']}", r, failures, run_index)
            return

    ctx = client.get("/api/calendar/schedule-context", params={"date": anchor_date})
    if ctx.status_code != 200:
        _fail("schedule-context", ctx, failures, run_index)
    elif ctx.json().get("mode") != "cram":
        failures.append(
            f"[試行 {run_index + 1}] schedule-context: mode={ctx.json().get('mode')}（期待 cram）"
        )

    t_sched = client.get(
        "/api/shifts/my-schedule",
        params={"role": "teacher", "entity_id": teacher_id, "period_id": period_id},
    )
    if t_sched.status_code != 200:
        _fail("講師スケジュール（提案後）", t_sched, failures, run_index)
    elif not t_sched.json().get("schedule_requested"):
        failures.append(f"[試行 {run_index + 1}] 講師: schedule_requested が false（提案書送付後）")

    # 5. スケジュール入力（生徒・講師一括提出）
    student_submissions = [
        {"date": d, "slots": _student_slots(**{"1": "", "4": ""})}
        for d in open_dates
    ]
    s_bulk = client.patch(
        "/api/shifts/bulk",
        json={
            "role": "student",
            "entity_id": student["id"],
            "period_id": period_id,
            "submissions": student_submissions,
        },
    )
    if s_bulk.status_code != 200:
        _fail("生徒スケジュール提出", s_bulk, failures, run_index)
        return

    teacher_submissions = [
        {"date": d, "slots": _empty_teacher_slots(**{"1": "", "3": "", "4": "", "5": ""})}
        for d in open_dates
    ]
    t_bulk = client.patch(
        "/api/shifts/bulk",
        json={
            "role": "teacher",
            "entity_id": teacher_id,
            "period_id": period_id,
            "submissions": teacher_submissions,
        },
    )
    if t_bulk.status_code != 200:
        _fail("講師スケジュール提出", t_bulk, failures, run_index)
        return

    # 6. 割り当て（自動 + 手動）
    auto_day = client.post("/api/admin/auto-assign", json={"date": anchor_date})
    if auto_day.status_code != 200:
        _fail("1日自動割当", auto_day, failures, run_index)

    auto_period = client.post(
        "/api/admin/auto-assign-period",
        json={
            "period_id": period_id,
            "rules": {
                "no_teacher_gaps": True,
                "weekly_limits": {"数学": 2, "英語": 2, "国語": 1},
            },
        },
    )
    if auto_period.status_code != 200:
        _fail("期間自動割当", auto_period, failures, run_index)

    manual = client.post(
        "/api/admin/assignments/manual",
        json={
            "date": open_dates[min(1, len(open_dates) - 1)],
            "student_name": students[1]["name"] if len(students) > 1 else student["name"],
            "subject": "国語",
            "teacher_id": teacher_id,
            "slot": 4,
            "period_id": period_id,
            "skip_rules": True,
            "is_fixed": False,
        },
    )
    if manual.status_code != 200:
        _fail("手動講習割当", manual, failures, run_index)

    sheets = client.get("/api/admin/assignments/sheets", params={"period_id": period_id}).json()
    ready_students = [s for s in sheets.get("students", []) if s.get("pending_count") == 0]

    # 7. 確定提出
    for s in ready_students[:2]:
        pub = client.post(
            "/api/admin/assignments/publish-schedule",
            json={"period_id": period_id, "student_id": s["id"]},
        )
        if pub.status_code != 200:
            _fail(f"生徒確定 student={s['id']}", pub, failures, run_index)

    for t in teachers[:2]:
        pub_t = client.post(
            "/api/admin/assignments/publish-teacher-schedule",
            json={"period_id": period_id, "teacher_id": t["id"]},
        )
        if pub_t.status_code != 200:
            _fail(f"講師確定 teacher={t['id']}", pub_t, failures, run_index)

    publish_all = client.post(
        "/api/admin/assignments/publish-all",
        json={"period_id": period_id},
    )
    if publish_all.status_code != 200:
        _fail("一括確定送付", publish_all, failures, run_index)

    finalize = client.patch(
        f"/api/admin/periods/{period_id}/status",
        json={"status": "FINALIZED", "force": True},
    )
    if finalize.status_code != 200:
        _fail("シフト確定 FINALIZED", finalize, failures, run_index)
        return

    export = client.get("/api/export/juku-schedule", params={"period_id": period_id})
    if export.status_code != 200:
        _fail("時間割 Excel 出力", export, failures, run_index)
    elif len(export.content) < 100:
        failures.append(f"[試行 {run_index + 1}] 時間割 Excel: ファイルが小さすぎる")

    readonly = client.get(
        "/api/shifts/my-schedule",
        params={"role": "student", "entity_id": student["id"], "period_id": period_id},
    )
    if readonly.status_code != 200:
        _fail("生徒確定後スケジュール", readonly, failures, run_index)
    elif not readonly.json().get("readonly"):
        failures.append(f"[試行 {run_index + 1}] 確定後: 生徒 readonly が false")


@pytest.fixture(scope="module")
def client():
    from main import app
    from security import create_access_token

    test_client = TestClient(app)
    token = create_access_token({"sub": "admin@example.com", "role": "admin", "name": "教室長"})
    test_client.headers["Authorization"] = f"Bearer {token}"
    return test_client


def test_cram_workflow_ten_runs(client: TestClient):
    failures: list[str] = []
    for run_index in range(RUN_COUNT):
        _run_single_workflow(client, run_index, failures)

    if failures:
        unique = list(dict.fromkeys(failures))
        summary = "\n".join(f"  - {f}" for f in unique)
        pytest.fail(
            f"講習フロー E2E: {len(unique)} 件の問題（{RUN_COUNT} 試行）\n{summary}"
        )
