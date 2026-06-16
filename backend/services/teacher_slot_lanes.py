"""講師コマの2レーン（通常 / 講習）表現。"""

from __future__ import annotations

from typing import Any

REGULAR_AVAIL = frozenset({"◎", "通常授業"})
BLOCKED_AVAIL = frozenset({"×", "不可"})

MAX_TEACHER_LANES = 2


def _lane_dict(
    lane: str,
    *,
    lesson_kind: str | None = None,
    student_name: str | None = None,
    subject: str | None = None,
    assignment: dict | None = None,
    occupied: bool = False,
    blocked: bool = False,
) -> dict[str, Any]:
    return {
        "lane": lane,
        "lesson_kind": lesson_kind,
        "student_name": student_name,
        "subject": subject,
        "assignment": assignment,
        "occupied": occupied,
        "blocked": blocked,
    }


def build_teacher_lanes(avail: str, assignments: list[dict]) -> list[dict]:
    """1コマを2レーンに分割。Lane A は通常（◎）優先、Lane B は講習割当用。"""
    if avail in BLOCKED_AVAIL:
        return [
            _lane_dict("a", blocked=True, occupied=True),
            _lane_dict("b", blocked=True, occupied=True),
        ]

    queue = list(assignments)
    regular = avail in REGULAR_AVAIL

    if regular:
        lane_a = _lane_dict("a", lesson_kind="通常", occupied=True)
        if queue:
            assign = queue.pop(0)
            lane_b = _lane_dict(
                "b",
                lesson_kind="講習",
                student_name=assign.get("student_name"),
                subject=assign.get("subject"),
                assignment=assign,
                occupied=True,
            )
        else:
            lane_b = _lane_dict("b")
        return [lane_a, lane_b]

    lane_a = _lane_dict("a")
    lane_b = _lane_dict("b")
    if queue:
        assign = queue.pop(0)
        lane_a = _lane_dict(
            "a",
            lesson_kind="講習",
            student_name=assign.get("student_name"),
            subject=assign.get("subject"),
            assignment=assign,
            occupied=True,
        )
    if queue:
        assign = queue.pop(0)
        lane_b = _lane_dict(
            "b",
            lesson_kind="講習",
            student_name=assign.get("student_name"),
            subject=assign.get("subject"),
            assignment=assign,
            occupied=True,
        )
    return [lane_a, lane_b]


def teacher_slot_assignable(avail: str, assignments: list[dict]) -> bool:
    lanes = build_teacher_lanes(avail, assignments)
    return any(not lane["occupied"] and not lane["blocked"] for lane in lanes)


def free_teacher_lane_count(avail: str, assignments: list[dict]) -> int:
    lanes = build_teacher_lanes(avail, assignments)
    return sum(1 for lane in lanes if not lane["occupied"] and not lane["blocked"])
