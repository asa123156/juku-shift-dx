"""講師2レーンのユニットテスト。"""

from services.assignment_engine import Teacher, get_assignment_candidates
from services.match_rules import MatchRules
from services.teacher_slot_lanes import build_teacher_lanes, teacher_slot_assignable


def test_regular_lane_leaves_second_for_cram() -> None:
    lanes = build_teacher_lanes("◎", [])
    assert lanes[0]["lesson_kind"] == "通常"
    assert lanes[0]["occupied"] is True
    assert lanes[1]["occupied"] is False
    assert teacher_slot_assignable("◎", [])


def test_regular_with_one_assignment_fills_lane_b() -> None:
    assign = {"student_name": "太郎", "subject": "数学", "slot": 1}
    lanes = build_teacher_lanes("◎", [assign])
    assert lanes[0]["lesson_kind"] == "通常"
    assert lanes[1]["lesson_kind"] == "講習"
    assert lanes[1]["student_name"] == "太郎"
    assert not teacher_slot_assignable("◎", [assign])


def test_assignment_allowed_on_regular_slot() -> None:
    teachers = [_teacher(1, "田中", {1: "◎", 2: "", 3: "", 4: ""})]
    rules = MatchRules(no_teacher_gaps=False, weekly_limits={"数学": 0})
    open_slots = {1: "", 2: "", 3: "", 4: ""}
    result = get_assignment_candidates(
        1, "数学", teachers, [], "2026-06-10", rules=rules, student_slots=open_slots
    )
    assert any(c["teacher_id"] == 1 and c["slot"] == 1 for c in result)


def _teacher(tid: int, name: str, slots: dict[int, str]) -> Teacher:
    return Teacher(id=tid, name=name, slots=slots)


def run_tests() -> None:
    test_regular_lane_leaves_second_for_cram()
    test_regular_with_one_assignment_fills_lane_b()
    test_assignment_allowed_on_regular_slot()
    print("teacher slot lanes tests passed.")


if __name__ == "__main__":
    run_tests()
