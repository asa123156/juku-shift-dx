"""自動割当ルールのユニットテスト。実行: cd backend && python -m tests.test_assignment_engine"""

from services.assignment_engine import (
    Teacher,
    get_assignment_candidates,
    has_consecutive_subject,
    is_three_consecutive_for_teacher,
)

DATE = "2026-06-10"


def _teacher(tid: int, name: str, slots: dict[int, str]) -> Teacher:
    return Teacher(id=tid, name=name, slots=slots)


def test_rejects_unavailable_teacher_slot() -> None:
    teachers = [_teacher(1, "田中", {1: "不可", 2: "待機", 3: "待機", 4: "待機"})]
    result = get_assignment_candidates(1, "数学I", teachers, [], DATE)
    assert all(c["slot"] != 1 for c in result)


def test_rejects_consecutive_same_subject() -> None:
    teachers = [_teacher(1, "田中", {1: "待機", 2: "待機", 3: "待機", 4: "待機"})]
    assignments = [
        {"date": DATE, "student_id": 1, "subject": "数学I", "teacher_id": 2, "slot": 1},
    ]
    assert has_consecutive_subject(1, "数学I", 2, assignments, DATE) is True
    result = get_assignment_candidates(1, "数学I", teachers, assignments, DATE)
    assert all(c["slot"] != 2 for c in result)


def test_rejects_three_consecutive_teacher_slots() -> None:
    assignments = [
        {"date": DATE, "student_id": 1, "subject": "英語", "teacher_id": 1, "slot": 1},
        {"date": DATE, "student_id": 2, "subject": "国語", "teacher_id": 1, "slot": 2},
    ]
    assert is_three_consecutive_for_teacher(1, 3, assignments, DATE) is True
    teachers = [_teacher(1, "田中", {1: "確定", 2: "確定", 3: "待機", 4: "待機"})]
    result = get_assignment_candidates(3, "数学I", teachers, assignments, DATE)
    assert all(not (c["teacher_id"] == 1 and c["slot"] == 3) for c in result)


def test_returns_valid_candidate() -> None:
    teachers = [
        _teacher(1, "田中", {1: "不可", 2: "確定", 3: "不可", 4: "不可"}),
        _teacher(3, "鈴木", {1: "待機", 2: "待機", 3: "確定", 4: "待機"}),
    ]
    result = get_assignment_candidates(1, "数学I", teachers, [], DATE)
    assert len(result) > 0
    assert any(c["teacher_id"] == 3 for c in result)


def run_tests() -> None:
    test_rejects_unavailable_teacher_slot()
    test_rejects_consecutive_same_subject()
    test_rejects_three_consecutive_teacher_slots()
    test_returns_valid_candidate()
    print("Assignment engine tests passed.")


if __name__ == "__main__":
    run_tests()
