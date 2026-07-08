"""科目ごとの担当講師設定のテスト。"""

from scripts.generate_demo_data import main as generate_demo
from services.assignment_engine import Teacher, get_assignment_candidates, pick_best_candidate
from services.assignment_store import reset_assignments_for_tests
from services.entity_store import reset_entities_for_tests
from services.period_store import get_period, list_periods, reset_periods_for_tests
from services.student_plan_store import (
    get_preferred_teacher_id,
    list_plans_for_student,
    reset_student_plans_for_tests,
    save_student_plans,
)


def _teacher_list() -> list[Teacher]:
    return [
        Teacher(id=1, name="田中 先生", slots={i: "" for i in range(1, 8)}),
        Teacher(id=2, name="佐藤 先生", slots={i: "" for i in range(1, 8)}),
    ]


def test_save_plans_with_teacher_id() -> None:
    generate_demo()
    reset_periods_for_tests()
    reset_entities_for_tests()
    reset_assignments_for_tests()
    reset_student_plans_for_tests()

    _, active_id = list_periods()
    assert active_id is not None

    saved, _ = save_student_plans(
        active_id,
        1,
        [
            {"subject": "数学", "slot_count": 2, "teacher_id": 2},
            {"subject": "英語", "slot_count": 1, "teacher_id": None},
        ],
    )
    assert saved[0]["teacher_id"] == 2
    assert saved[0]["teacher_name"] == "佐藤 先生"
    assert saved[1]["teacher_id"] is None

    assert get_preferred_teacher_id(active_id, 1, "数学") == 2
    assert get_preferred_teacher_id(active_id, 1, "英語") is None


def test_preferred_teacher_limits_candidates() -> None:
    generate_demo()
    reset_periods_for_tests()
    reset_entities_for_tests()
    reset_student_plans_for_tests()

    _, active_id = list_periods()
    save_student_plans(active_id, 1, [{"subject": "数学", "slot_count": 1, "teacher_id": 2}])

    date = get_period(active_id).start_date
    candidates = get_assignment_candidates(
        student_id=1,
        subject="数学",
        teacher_list=_teacher_list(),
        current_assignments=[],
        date=date,
        preferred_teacher_id=2,
    )
    assert candidates
    assert all(c["teacher_id"] == 2 for c in candidates)

    best = pick_best_candidate(
        student_id=1,
        subject="数学",
        teacher_list=_teacher_list(),
        current_assignments=[],
        date=date,
        preferred_teacher_id=2,
    )
    assert best is not None
    assert best["teacher_id"] == 2

    no_match = pick_best_candidate(
        student_id=1,
        subject="数学",
        teacher_list=_teacher_list(),
        current_assignments=[],
        date=date,
        preferred_teacher_id=99,
    )
    assert no_match is None
