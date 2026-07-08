"""時間割表（assignments）正本ロジックのテスト。"""

from services.assignment_store import add_assignment, reset_assignments_for_tests
from services.period_store import get_period
from services.schedule_canonical import (
    compute_student_pending_count,
    derive_pending_requests,
    derive_unassigned_by_date,
    student_assignments_for_period,
)
from schemas.assignment import AssignmentRecord
from services.student_plan_store import reset_student_plans_for_tests, save_student_plans


def test_pending_derived_from_grid_not_requests():
    reset_assignments_for_tests()
    reset_student_plans_for_tests()
    period = get_period(1)
    save_student_plans(1, 1, [{"subject": "数学", "slot_count": 2}])

    assert len(derive_pending_requests(1)) == 2
    pending_by_date = derive_unassigned_by_date(1)
    assert pending_by_date
    assert all(len(v) == 2 for v in pending_by_date.values())

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
    assert len(derive_pending_requests(1)) == 1
    pending_after = derive_unassigned_by_date(1)
    assert all(len(v) == 1 for v in pending_after.values())

    plans = [{"subject": "数学", "slot_count": 2}]
    rows = student_assignments_for_period(1, 1)
    assert compute_student_pending_count(1, plans, rows) == 1
