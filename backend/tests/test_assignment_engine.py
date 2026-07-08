"""自動割当ルールのユニットテスト。実行: cd backend && python -m tests.test_assignment_engine"""

from services.assignment_engine import (
    Teacher,
    get_assignment_candidates,
)
from services.match_rules import MatchRules

DATE = "2026-06-10"
DATE2 = "2026-06-11"
DATE3 = "2026-06-12"


def _teacher(tid: int, name: str, slots: dict[int, str]) -> Teacher:
    return Teacher(id=tid, name=name, slots=slots)


def _student_slots(slots: list[int] | None = None) -> dict[int, str]:
    nums = slots if slots is not None else list(range(1, 7))
    return {n: "" for n in nums}


def test_rejects_unavailable_teacher_slot() -> None:
    teachers = [_teacher(1, "田中", {1: "不可", 2: "待機", 3: "待機", 4: "待機"})]
    result = get_assignment_candidates(
        1, "数学I", teachers, [], DATE, student_slots=_student_slots([1, 2, 3, 4])
    )
    assert all(c["slot"] != 1 for c in result)


def test_weekly_math_limit() -> None:
    teachers = [_teacher(1, "田中", {1: "待機", 2: "待機", 3: "待機", 4: "待機"})]
    pool = [
        {"date": DATE, "student_id": 1, "subject": "数学I", "teacher_id": 1, "slot": 1},
        {"date": DATE2, "student_id": 1, "subject": "数学I", "teacher_id": 1, "slot": 1},
    ]
    rules = MatchRules(weekly_limits={"数学": 2})
    result = get_assignment_candidates(
        1, "数学I", teachers, pool, DATE3, rules=rules, all_assignments=pool,
        student_slots=_student_slots(),
    )
    assert result == []


def test_weekly_kokugo_limit() -> None:
    teachers = [_teacher(1, "田中", {1: "待機", 2: "待機", 3: "待機", 4: "待機"})]
    pool = [
        {"date": DATE, "student_id": 1, "subject": "国語", "teacher_id": 1, "slot": 2},
    ]
    rules = MatchRules(weekly_limits={"国語": 1})
    result = get_assignment_candidates(
        1, "国語", teachers, [], DATE2, rules=rules, all_assignments=pool,
        student_slots=_student_slots(),
    )
    assert result == []


def test_no_teacher_gap_rule() -> None:
    teachers = [_teacher(1, "田中", {1: "待機", 2: "待機", 3: "待機", 4: "待機"})]
    assignments = [
        {"date": DATE, "student_id": 2, "subject": "英語", "teacher_id": 1, "slot": 1},
    ]
    rules = MatchRules(no_teacher_gaps=True, weekly_limits={})
    result = get_assignment_candidates(
        1, "数学I", teachers, assignments, DATE, rules=rules,
        student_slots=_student_slots(),
    )
    assert all(not (c["teacher_id"] == 1 and c["slot"] == 3) for c in result)


def test_student_three_consecutive_limit() -> None:
    teachers = [_teacher(1, "田中", {1: "待機", 2: "待機", 3: "待機", 4: "待機"})]
    assignments = [
        {"date": DATE, "student_id": 1, "subject": "数学", "teacher_id": 1, "slot": 1},
        {"date": DATE, "student_id": 1, "subject": "国語", "teacher_id": 1, "slot": 2},
    ]
    rules = MatchRules(no_teacher_gaps=False, weekly_limits={"英語": 0})
    open_slots = {1: "", 2: "", 3: "", 4: ""}
    result = get_assignment_candidates(
        1, "英語", teachers, assignments, DATE, rules=rules, student_slots=open_slots
    )
    assert all(c["slot"] != 3 for c in result)
    assert any(c["slot"] == 4 for c in result)


def test_teacher_four_consecutive_limit() -> None:
    teachers = [_teacher(1, "田中", {1: "待機", 2: "待機", 3: "待機", 4: "待機", 5: "待機", 6: "待機"})]
    assignments = [
        {"date": DATE, "student_id": 2, "subject": "数学", "teacher_id": 1, "slot": 1},
        {"date": DATE, "student_id": 3, "subject": "国語", "teacher_id": 1, "slot": 2},
        {"date": DATE, "student_id": 4, "subject": "英語", "teacher_id": 1, "slot": 3},
    ]
    rules = MatchRules(no_teacher_gaps=False, weekly_limits={"理科": 0})
    result = get_assignment_candidates(
        1, "理科", teachers, assignments, DATE, rules=rules,
        student_slots=_student_slots(),
    )
    assert all(not (c["teacher_id"] == 1 and c["slot"] == 4) for c in result)
    assert any(c["teacher_id"] == 1 and c["slot"] == 5 for c in result)


def test_weekly_limit_absorbs_arithmetic_into_math() -> None:
    teachers = [_teacher(1, "田中", {1: "待機", 2: "待機", 3: "待機", 4: "待機"})]
    pool = [
        {"date": DATE, "student_id": 1, "subject": "算数", "teacher_id": 1, "slot": 1},
        {"date": DATE2, "student_id": 1, "subject": "数学", "teacher_id": 1, "slot": 1},
    ]
    rules = MatchRules(weekly_limits={"数学": 2})
    result = get_assignment_candidates(
        1, "算数", teachers, pool, DATE3, rules=rules, all_assignments=pool,
        student_slots=_student_slots(),
    )
    assert result == []


def test_weekly_limit_absorbs_physics_chemistry_into_science() -> None:
    teachers = [_teacher(1, "田中", {1: "待機", 2: "待機", 3: "待機", 4: "待機"})]
    pool = [
        {"date": DATE, "student_id": 1, "subject": "物理", "teacher_id": 1, "slot": 1},
        {"date": DATE2, "student_id": 1, "subject": "化学", "teacher_id": 1, "slot": 1},
    ]
    rules = MatchRules(weekly_limits={"理科": 2})
    result = get_assignment_candidates(
        1, "理科", teachers, pool, DATE3, rules=rules, all_assignments=pool,
        student_slots=_student_slots(),
    )
    assert result == []


def test_no_weekly_limit_when_zero() -> None:
    teachers = [_teacher(1, "田中", {1: "待機", 2: "待機", 3: "待機", 4: "待機"})]
    pool = [
        {"date": DATE, "student_id": 1, "subject": "英語", "teacher_id": 1, "slot": 1},
        {"date": DATE2, "student_id": 1, "subject": "英語", "teacher_id": 1, "slot": 1},
    ]
    rules = MatchRules(weekly_limits={"英語": 0})
    result = get_assignment_candidates(
        1, "英語", teachers, pool, DATE3, rules=rules, all_assignments=pool,
        student_slots=_student_slots(),
    )
    assert len(result) > 0


def test_rejects_student_unavailable_slot() -> None:
    teachers = [_teacher(1, "田中", {1: "待機", 2: "待機", 3: "待機", 4: "待機"})]
    student_slots = {1: "×", 2: "", 3: "", 4: ""}
    result = get_assignment_candidates(
        1, "数学I", teachers, [], DATE, student_slots=student_slots
    )
    assert all(c["slot"] != 1 for c in result)
    assert any(c["slot"] == 2 for c in result)
    assert any(c["slot"] == 4 for c in result)


def test_assignable_on_empty_slots() -> None:
    teachers = [_teacher(1, "田中", {1: "待機", 2: "待機", 3: "待機", 4: "待機"})]
    student_slots = {1: "", 2: "", 3: "", 4: ""}
    result = get_assignment_candidates(
        1, "数学I", teachers, [], DATE, student_slots=student_slots
    )
    assert any(c["slot"] == 1 for c in result)
    assert any(c["slot"] == 4 for c in result)


def run_tests() -> None:
    test_rejects_unavailable_teacher_slot()
    test_rejects_student_unavailable_slot()
    test_assignable_on_empty_slots()
    test_weekly_math_limit()
    test_weekly_kokugo_limit()
    test_no_teacher_gap_rule()
    test_student_three_consecutive_limit()
    test_teacher_four_consecutive_limit()
    test_weekly_limit_absorbs_arithmetic_into_math()
    test_weekly_limit_absorbs_physics_chemistry_into_science()
    test_no_weekly_limit_when_zero()
    print("Assignment engine tests passed.")


if __name__ == "__main__":
    run_tests()
