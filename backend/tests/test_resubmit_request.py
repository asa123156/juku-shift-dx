"""提出後の変更申請（再提出）のテスト。"""

from services.assignment_store import add_assignment, reset_assignments_for_tests
from services.change_request_store import create_resubmit_request, resolve_change_request
from services.class_schedule_store import get_schedules_between
from services.schedule_publish_store import publish_student_schedule_request
from services.student_plan_store import reset_student_plans_for_tests, save_student_plans
from schemas.assignment import AssignmentRecord
from services.submission_store import get_entity_day, is_entity_fully_submitted, reset_submissions_for_tests
from services.period_store import get_period, open_dates_for_period


def test_resubmit_clears_student_assignments():
    reset_assignments_for_tests()
    reset_submissions_for_tests()
    reset_student_plans_for_tests()
    period = get_period(1)
    open_dates = open_dates_for_period(period)
    save_student_plans(1, 1, [{"subject": "数学", "slot_count": 1}])
    publish_student_schedule_request(1, 1)

    add_assignment(
        AssignmentRecord(
            date=period.start_date,
            student_id=1,
            student_name="山田太郎",
            subject="数学",
            teacher_id=1,
            teacher_name="田中",
            slot=1,
        )
    )
    from services.schedule_service import bulk_save_submissions
    from schemas.period import empty_slots

    bulk_save_submissions(
        "student",
        1,
        1,
        [{"date": d, "slots": empty_slots()} for d in open_dates],
    )
    assert is_entity_fully_submitted("student", 1, open_dates)

    row = create_resubmit_request(1, "student", 1, reason="都合変更")
    resolved = resolve_change_request(row["id"], "approve")
    assert resolved["request_type"] == "RESUBMIT"

    tutoring = [
        r
        for r in get_schedules_between(period.start_date, period.end_date)
        if r["student_id"] == 1 and not r.get("is_fixed")
    ]
    assert tutoring == []
    assert get_entity_day("student", 1, open_dates[0]) is None
