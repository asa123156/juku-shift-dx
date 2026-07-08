"""講師コマの可変レーン（1対2 / 1対4）表現。"""

from __future__ import annotations

from typing import Any

REGULAR_AVAIL = frozenset({"通常授業"})
BLOCKED_AVAIL = frozenset({"×", "不可"})

MAX_TEACHER_LANES = 4
LANE_LABELS = ("a", "b", "c", "d")


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


def _clamp_max_lanes(max_lanes: int) -> int:
    return max(1, min(int(max_lanes), MAX_TEACHER_LANES))


def build_teacher_lanes(
    avail: str,
    assignments: list[dict],
    max_lanes: int = MAX_TEACHER_LANES,
) -> list[dict]:
    """1コマを max_lanes レーンに分割。Lane A は通常（◎）優先、残りは講習割当用。"""
    max_lanes = _clamp_max_lanes(max_lanes)
    lane_ids = LANE_LABELS[:max_lanes]

    if avail in BLOCKED_AVAIL:
        return [_lane_dict(lid, blocked=True, occupied=True) for lid in lane_ids]

    queue = list(assignments)

    def _is_regular(a: dict) -> bool:
        if a.get("is_fixed"):
            return True
        return (a.get("lesson_kind") or "") == "通常"

    regular_slot = any(_is_regular(a) for a in queue)
    regular_assignment = next((a for a in queue if _is_regular(a)), None)
    if regular_assignment is not None:
        queue.remove(regular_assignment)

    lanes: list[dict] = []

    if regular_slot:
        if regular_assignment is not None:
            lanes.append(
                _lane_dict(
                    "a",
                    lesson_kind="通常",
                    student_name=regular_assignment.get("student_name"),
                    subject=regular_assignment.get("subject"),
                    assignment=regular_assignment,
                    occupied=True,
                )
            )
        else:
            lanes.append(_lane_dict("a", lesson_kind="通常", occupied=True))
    elif queue:
        assign = queue.pop(0)
        lanes.append(
            _lane_dict(
                "a",
                lesson_kind=assign.get("lesson_kind") or "講習",
                student_name=assign.get("student_name"),
                subject=assign.get("subject"),
                assignment=assign,
                occupied=True,
            )
        )
    else:
        lanes.append(_lane_dict("a"))

    for lid in lane_ids[1:]:
        if queue:
            assign = queue.pop(0)
            lanes.append(
                _lane_dict(
                    lid,
                    lesson_kind=assign.get("lesson_kind") or "講習",
                    student_name=assign.get("student_name"),
                    subject=assign.get("subject"),
                    assignment=assign,
                    occupied=True,
                )
            )
        else:
            lanes.append(_lane_dict(lid))

    return lanes


def teacher_slot_assignable(avail: str, assignments: list[dict], max_lanes: int = MAX_TEACHER_LANES) -> bool:
    lanes = build_teacher_lanes(avail, assignments, max_lanes=max_lanes)
    return any(not lane["occupied"] and not lane["blocked"] for lane in lanes)


def free_teacher_lane_count(avail: str, assignments: list[dict], max_lanes: int = MAX_TEACHER_LANES) -> int:
    lanes = build_teacher_lanes(avail, assignments, max_lanes=max_lanes)
    return sum(1 for lane in lanes if not lane["occupied"] and not lane["blocked"])
