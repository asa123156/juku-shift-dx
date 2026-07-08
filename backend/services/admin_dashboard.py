"""管理ダッシュボード用の集計。"""

from __future__ import annotations

from services.change_request_store import count_pending_requests, list_change_requests
from services.class_schedule_store import get_schedules_between
from services.entity_store import list_students, list_teachers
from services.period_store import get_period, open_dates_for_period
from services.schedule_publish_store import (
    list_published_student_ids,
    list_published_teacher_ids,
    list_request_published_student_ids,
    list_request_published_teacher_ids,
)
from services.student_plan_store import list_plans_for_period
from services.submission_store import get_submissions_for_date


def _is_unsubmitted(role: str, entity_id: int, open_dates: list[str]) -> bool:
    if not open_dates:
        return False
    for iso_date in open_dates:
        if entity_id not in get_submissions_for_date(role, iso_date):
            return True
    return False


def _student_row(student: dict) -> dict:
    return {
        "id": student["id"],
        "name": student["name"],
        "grade_label": student.get("grade_label", ""),
    }


def _teacher_row(teacher: dict) -> dict:
    return {
        "id": teacher["id"],
        "name": teacher["name"],
        "color": teacher.get("color", ""),
    }


def _step_status(*, done: bool, active: bool) -> str:
    if done:
        return "done"
    if active:
        return "active"
    return "pending"


def build_workflow_status(period_id: int) -> list[dict]:
    """教室長向け6ステップの進捗。"""
    from services.assignment_sheets import build_assignment_sheets

    period = get_period(period_id)
    open_dates = open_dates_for_period(period)
    all_students = list_students()
    plans_by_student = list_plans_for_period(period_id)
    students_with_plans = sum(1 for s in all_students if plans_by_student.get(s["id"]))
    fixed_rows = get_schedules_between(period.start_date, period.end_date, fixed_only=True)
    request_published = list_request_published_student_ids(period_id)
    teacher_request_published = list_request_published_teacher_ids(period_id)
    schedule_published = list_published_student_ids(period_id)
    teacher_schedule_published = list_published_teacher_ids(period_id)
    sheets = build_assignment_sheets(period_id)
    pending_total = int(sheets.get("pending_total") or 0)
    student_count = len(all_students)
    teacher_count = len(list_teachers())

    unsubmitted_students = sum(
        1 for s in all_students if _is_unsubmitted("student", s["id"], open_dates)
    )
    unsubmitted_teachers = sum(
        1 for t in list_teachers() if _is_unsubmitted("teacher", t["id"], open_dates)
    )

    step1_done = student_count > 0 and students_with_plans > 0
    step2_done = len(fixed_rows) > 0
    students_proposal_ok = student_count == 0 or len(request_published) >= student_count
    teachers_proposal_ok = teacher_count == 0 or len(teacher_request_published) >= teacher_count
    step3_done = students_proposal_ok and teachers_proposal_ok
    step4_done = (
        step3_done
        and unsubmitted_students == 0
        and unsubmitted_teachers == 0
        and open_dates
    )
    step5_done = pending_total == 0 and step4_done
    students_final_ok = student_count == 0 or len(schedule_published) >= student_count
    teachers_final_ok = teacher_count == 0 or len(teacher_schedule_published) >= teacher_count
    step6_done = period.status == "FINALIZED" or (students_final_ok and teachers_final_ok)

    steps = [
        {
            "id": 1,
            "title": "講習作成・希望設定",
            "description": "講習期間を作成し、生徒の希望科目を設定",
            "path": "/admin/manage",
            "alt_path": "/admin/student-plans",
            "status": _step_status(done=step1_done, active=not step1_done),
            "detail": f"希望設定 {students_with_plans}/{student_count} 名",
        },
        {
            "id": 2,
            "title": "通常授業の入力",
            "description": "Excel取込 または 時間割表で通常授業を入力",
            "path": "/import",
            "alt_path": "/admin/schedule-grid",
            "status": _step_status(done=step2_done, active=step1_done and not step2_done),
            "detail": f"通常授業 {len(fixed_rows)} 件",
        },
        {
            "id": 3,
            "title": "提案書を送付",
            "description": "生徒・講師に講習の日程提案書を配布",
            "path": "/admin/assignments",
            "status": _step_status(done=step3_done, active=step2_done and not step3_done),
            "detail": (
                f"生徒 {len(request_published)}/{student_count} · "
                f"講師 {len(teacher_request_published)}/{teacher_count}"
            ),
        },
        {
            "id": 4,
            "title": "スケジュール提出",
            "description": "生徒・講師が空き / × を提出",
            "path": "/admin",
            "status": _step_status(done=step4_done, active=step3_done and not step4_done),
            "detail": f"未提出 生徒{unsubmitted_students}・講師{unsubmitted_teachers}",
        },
        {
            "id": 5,
            "title": "割当・時間割調整",
            "description": "生徒を講師に割り当て、時間割表で調整",
            "path": "/admin/assignments",
            "alt_path": "/admin/schedule-grid",
            "status": _step_status(done=step5_done, active=step4_done and not step5_done),
            "detail": f"未割当 {pending_total} 件",
        },
        {
            "id": 6,
            "title": "確定・送信",
            "description": "確定スケジュールを生徒・講師に送信",
            "path": "/admin/assignments",
            "status": _step_status(done=step6_done, active=step5_done and not step6_done),
            "detail": (
                f"生徒 {len(schedule_published)}/{student_count} · "
                f"講師 {len(teacher_schedule_published)}/{teacher_count}"
            ),
        },
    ]
    return steps


def build_admin_dashboard_summary(period_id: int) -> dict:
    period = get_period(period_id)
    open_dates = open_dates_for_period(period)
    schedules = get_schedules_between(period.start_date, period.end_date)

    students_on_grid = {row["student_id"] for row in schedules}
    teachers_on_grid = {row["teacher_id"] for row in schedules}

    request_published = list_request_published_student_ids(period_id)
    teacher_request_published = list_request_published_teacher_ids(period_id)
    schedule_published = list_published_student_ids(period_id)
    teacher_published = list_published_teacher_ids(period_id)

    all_students = list_students()
    all_teachers = list_teachers()
    student_by_id = {s["id"]: s for s in all_students}
    teacher_by_id = {t["id"]: t for t in all_teachers}

    students_proposal_sent = sorted(
        [
            _student_row(student_by_id[sid])
            for sid in request_published
            if sid in student_by_id
        ],
        key=lambda x: x["name"],
    )
    students_schedule_published = sorted(
        [
            _student_row(student_by_id[sid])
            for sid in schedule_published
            if sid in student_by_id
        ],
        key=lambda x: x["name"],
    )
    students_unsubmitted = sorted(
        [
            _student_row(s)
            for s in all_students
            if _is_unsubmitted("student", s["id"], open_dates)
        ],
        key=lambda x: x["name"],
    )

    teachers_proposal_sent = sorted(
        [
            _teacher_row(teacher_by_id[tid])
            for tid in teacher_request_published
            if tid in teacher_by_id
        ],
        key=lambda x: x["name"],
    )
    teachers_schedule_published = sorted(
        [
            _teacher_row(teacher_by_id[tid])
            for tid in teacher_published
            if tid in teacher_by_id
        ],
        key=lambda x: x["name"],
    )
    teachers_unsubmitted = sorted(
        [
            _teacher_row(t)
            for t in all_teachers
            if _is_unsubmitted("teacher", t["id"], open_dates)
        ],
        key=lambda x: x["name"],
    )

    pending_requests = list_change_requests(period_id, status="PENDING")

    return {
        "period_id": period_id,
        "period_name": period.name,
        "period_status": period.status,
        "open_days": len(open_dates),
        "students": {
            "proposal_sent": students_proposal_sent,
            "unsubmitted": students_unsubmitted,
            "schedule_published": students_schedule_published,
            "on_grid": len(students_on_grid),
        },
        "teachers": {
            "proposal_sent": teachers_proposal_sent,
            "unsubmitted": teachers_unsubmitted,
            "schedule_published": teachers_schedule_published,
            "on_grid": len(teachers_on_grid),
        },
        "pending_change_count": count_pending_requests(period_id),
        "change_requests": pending_requests,
        # 互換: 件数サマリ
        "students_with_schedule": len(students_on_grid),
        "teachers_with_schedule": len(teachers_on_grid),
        "students_proposal_sent": len(students_proposal_sent),
        "students_schedule_published": len(students_schedule_published),
        "teachers_proposal_sent": len(teachers_proposal_sent),
        "teachers_schedule_published": len(teachers_schedule_published),
        "unsubmitted_students": len(students_unsubmitted),
        "unsubmitted_teachers": len(teachers_unsubmitted),
        "workflow_steps": build_workflow_status(period_id),
    }
