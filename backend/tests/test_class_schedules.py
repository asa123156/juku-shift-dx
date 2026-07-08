"""class_schedules / is_fixed のテスト。"""

from services.assignment_store import add_assignment, reset_assignments_for_tests
from services.class_schedule_store import get_fixed_only_schedule, get_full_schedule, get_schedules_for_date
from schemas.assignment import AssignmentRecord
from services.period_store import get_period


def test_is_fixed_and_schedule_filters():
    reset_assignments_for_tests()
    period = get_period(1)
    add_assignment(
        AssignmentRecord(
            date=period.start_date,
            student_id=1,
            student_name="山田太郎",
            subject="数学",
            teacher_id=1,
            teacher_name="田中",
            slot=1,
            lesson_kind="通常",
        )
    )
    add_assignment(
        AssignmentRecord(
            date=period.start_date,
            student_id=2,
            student_name="佐藤花子",
            subject="英語",
            teacher_id=2,
            teacher_name="鈴木",
            slot=2,
            lesson_kind="講習",
        )
    )
    day = get_schedules_for_date(period.start_date)
    assert len(day) == 2
    fixed = get_schedules_for_date(period.start_date, fixed_only=True)
    assert len(fixed) == 1
    assert fixed[0]["is_fixed"] is True
    assert fixed[0]["lesson_kind"] == "通常"

    full = get_full_schedule(1)
    assert full["total"] == 2
    fixed_only = get_fixed_only_schedule(1)
    assert fixed_only["total"] == 1
