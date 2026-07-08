"""生徒希望（教科・コマ数）のテスト。"""

from scripts.generate_demo_data import main as generate_demo
from services.entity_store import reset_entities_for_tests
from services.period_store import get_period, reset_periods_for_tests, list_periods
from services.assignment_store import reset_assignments_for_tests
from services.schedule_canonical import derive_pending_requests
from services.student_plan_store import (
    list_plans_for_student,
    reset_student_plans_for_tests,
    save_student_plans,
)


def test_save_plans_syncs_requests() -> None:
    generate_demo()
    reset_periods_for_tests()
    reset_entities_for_tests()
    reset_assignments_for_tests()
    reset_student_plans_for_tests()

    periods, active_id = list_periods()
    assert active_id is not None

    saved, synced = save_student_plans(
        active_id,
        1,
        [
            {"subject": "数学", "slot_count": 2},
            {"subject": "英語", "slot_count": 1},
        ],
    )
    assert len(saved) == 2
    assert synced == 3

    plans = list_plans_for_student(active_id, 1)
    assert plans[0]["subject"] == "数学"
    assert plans[0]["slot_count"] == 2

    pending = derive_pending_requests(active_id)
    math_count = sum(1 for r in pending if r["student_id"] == 1 and r["subject"] == "数学")
    english_count = sum(1 for r in pending if r["student_id"] == 1 and r["subject"] == "英語")
    assert math_count == 2
    assert english_count == 1


def run_tests() -> None:
    test_save_plans_syncs_requests()
    print("student plan tests passed.")


if __name__ == "__main__":
    run_tests()
