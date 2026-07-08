"""講師2レーン / 4レーンのユニットテスト。"""

from services.assignment_engine import Teacher, get_assignment_candidates
from services.match_rules import MatchRules
from services.teacher_slot_lanes import build_teacher_lanes, teacher_slot_assignable


def _regular(name: str = "山田") -> dict:
    return {
        "student_name": name,
        "subject": "",
        "slot": 1,
        "is_fixed": True,
        "lesson_kind": "通常",
    }


def test_regular_lane_leaves_second_for_cram() -> None:
    lanes = build_teacher_lanes("", [_regular()], max_lanes=2)
    assert lanes[0]["lesson_kind"] == "通常"
    assert lanes[0]["occupied"] is True
    assert lanes[1]["occupied"] is False
    assert teacher_slot_assignable("", [_regular()], max_lanes=2)


def test_regular_with_one_assignment_fills_lane_b() -> None:
    cram = {"student_name": "太郎", "subject": "数学", "slot": 1}
    lanes = build_teacher_lanes("", [_regular(), cram], max_lanes=2)
    assert lanes[0]["lesson_kind"] == "通常"
    assert lanes[1]["lesson_kind"] == "講習"
    assert lanes[1]["student_name"] == "太郎"
    assert not teacher_slot_assignable("", [_regular(), cram], max_lanes=2)


def test_regular_assignment_uses_lane_a_details() -> None:
    assign = {"student_name": "花子", "subject": "英語", "slot": 1, "lesson_kind": "通常", "is_fixed": True}
    lanes = build_teacher_lanes("", [assign], max_lanes=2)
    assert lanes[0]["lesson_kind"] == "通常"
    assert lanes[0]["student_name"] == "花子"
    assert lanes[0]["subject"] == "英語"
    assert lanes[1]["occupied"] is False


def test_four_lanes_supports_three_cram_assignments() -> None:
    assigns = [
        {"student_name": "A", "subject": "数学", "slot": 1},
        {"student_name": "B", "subject": "英語", "slot": 1},
        {"student_name": "C", "subject": "国語", "slot": 1},
    ]
    lanes = build_teacher_lanes("", assigns, max_lanes=4)
    assert len(lanes) == 4
    assert lanes[0]["student_name"] == "A"
    assert lanes[1]["student_name"] == "B"
    assert lanes[2]["student_name"] == "C"
    assert lanes[3]["occupied"] is False
    assert teacher_slot_assignable("", assigns, max_lanes=4)


def test_four_lanes_full_when_four_assignments() -> None:
    assigns = [
        {"student_name": f"S{i}", "subject": "数学", "slot": 1} for i in range(4)
    ]
    lanes = build_teacher_lanes("", assigns, max_lanes=4)
    assert all(lane["occupied"] for lane in lanes)
    assert not teacher_slot_assignable("", assigns, max_lanes=4)


def test_assignment_allowed_on_regular_slot() -> None:
    teachers = [_teacher(1, "田中", {1: "", 2: "", 3: "", 4: ""})]
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
    test_regular_assignment_uses_lane_a_details()
    test_four_lanes_supports_three_cram_assignments()
    test_four_lanes_full_when_four_assignments()
    test_assignment_allowed_on_regular_slot()
    print("teacher slot lanes tests passed.")


if __name__ == "__main__":
    run_tests()
