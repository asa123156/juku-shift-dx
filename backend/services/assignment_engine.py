from dataclasses import dataclass

from services.match_rules import (
    MatchRules,
    SLOTS,
    exceeds_weekly_limit,
    weekly_limit_for,
    would_create_teacher_gap,
    would_violate_student_consecutive_limit,
    would_violate_teacher_consecutive_limit,
)
from services.student_slot_codec import (
    is_student_slot_assignable,
    student_slot_block_reason,
    student_slot_preference_bonus,
)
from services.student_store import get_student_submission
from services.teacher_slot_lanes import BLOCKED_AVAIL, free_teacher_lane_count


@dataclass
class Teacher:
    id: int
    name: str
    slots: dict[int, str]


def teachers_from_dashboard(dashboard: dict) -> list[Teacher]:
    teachers: list[Teacher] = []
    for row in dashboard.get("teachers", []):
        slots = {i: row[f"s{i}"] for i in SLOTS}
        teachers.append(Teacher(id=row["id"], name=row["name"], slots=slots))
    return teachers


MAX_STUDENTS_PER_TEACHER_SLOT = 2


def count_teacher_slot_assignments(
    teacher_id: int,
    slot: int,
    date: str,
    current_assignments: list[dict],
) -> int:
    return sum(
        1
        for a in current_assignments
        if a["date"] == date and a["teacher_id"] == teacher_id and a["slot"] == slot
    )


def is_teacher_slot_full(
    teacher_id: int,
    slot: int,
    current_assignments: list[dict],
    date: str,
) -> bool:
    return (
        count_teacher_slot_assignments(teacher_id, slot, date, current_assignments)
        >= MAX_STUDENTS_PER_TEACHER_SLOT
    )


def is_teacher_slot_occupied(
    teacher_id: int,
    slot: int,
    current_assignments: list[dict],
    date: str,
    teacher_slots: dict[int, str] | None = None,
) -> bool:
    avail = ""
    if teacher_slots is not None:
        avail = teacher_slots.get(slot, "")
    at_slot = [
        a
        for a in current_assignments
        if a["date"] == date and a["teacher_id"] == teacher_id and a["slot"] == slot
    ]
    if teacher_slots is not None:
        return free_teacher_lane_count(avail, at_slot) <= 0
    return len(at_slot) >= MAX_STUDENTS_PER_TEACHER_SLOT


def load_student_slots(student_id: int, iso_date: str) -> dict[int, str]:
    raw = get_student_submission(student_id, iso_date)
    if not raw:
        return {}
    return {slot: raw.get(str(slot), "") for slot in SLOTS}


def is_student_slot_occupied(
    student_id: int,
    slot: int,
    current_assignments: list[dict],
    date: str,
) -> bool:
    return any(
        a["date"] == date and a["student_id"] == student_id and a["slot"] == slot
        for a in current_assignments
    )


def get_assignment_candidates(
    student_id: int,
    subject: str,
    teacher_list: list[Teacher],
    current_assignments: list[dict],
    date: str,
    rules: MatchRules | None = None,
    all_assignments: list[dict] | None = None,
    student_slots: dict[int, str] | None = None,
) -> list[dict]:
    """全講師×全コマの組み合わせから、NGルールを通過した候補を返す。"""
    rules = rules or MatchRules()
    pool = all_assignments if all_assignments is not None else current_assignments
    if student_slots is None:
        student_slots = load_student_slots(student_id, date)
    valid_candidates: list[dict] = []

    for teacher in teacher_list:
        for slot in SLOTS:
            avail = teacher.slots.get(slot, "")
            if avail in BLOCKED_AVAIL:
                continue

            if is_teacher_slot_occupied(
                teacher.id, slot, current_assignments, date, teacher.slots
            ):
                continue

            if is_student_slot_occupied(student_id, slot, current_assignments, date):
                continue

            slot_symbol = student_slots.get(slot, "")
            if not is_student_slot_assignable(slot_symbol, subject):
                continue

            if exceeds_weekly_limit(student_id, subject, date, pool, rules):
                continue

            if rules.no_teacher_gaps and would_create_teacher_gap(
                teacher.id, slot, date, teacher.slots, current_assignments
            ):
                continue

            if would_violate_student_consecutive_limit(
                student_id, slot, date, current_assignments
            ):
                continue

            if would_violate_teacher_consecutive_limit(
                teacher.id, slot, date, teacher.slots, current_assignments
            ):
                continue

            valid_candidates.append(
                {
                    "teacher_id": teacher.id,
                    "teacher_name": teacher.name,
                    "slot": slot,
                }
            )

    return valid_candidates


def score_candidate(
    teacher: Teacher,
    slot: int,
    date: str,
    current_assignments: list[dict],
    rules: MatchRules | None = None,
    student_slots: dict[int, str] | None = None,
    subject: str = "",
) -> int:
    rules = rules or MatchRules()
    score = 90 if teacher.slots.get(slot, "") == "" else 60

    if rules.no_teacher_gaps:
        from services.match_rules import teacher_occupied_slots

        occupied = teacher_occupied_slots(teacher.id, date, teacher.slots, current_assignments)
        if (slot - 1) in occupied or (slot + 1) in occupied:
            score += 15

    if student_slots is not None and subject:
        score += student_slot_preference_bonus(student_slots.get(slot, ""), subject)

    return min(score, 100)


def rank_candidates(
    candidates: list[dict],
    teacher_list: list[Teacher],
    date: str,
    current_assignments: list[dict],
    rules: MatchRules | None = None,
    student_slots: dict[int, str] | None = None,
    subject: str = "",
) -> list[dict]:
    rules = rules or MatchRules()
    teacher_map = {t.id: t for t in teacher_list}
    ranked = []
    for c in candidates:
        teacher = teacher_map[c["teacher_id"]]
        ranked.append(
            {
                **c,
                "match_score": score_candidate(
                    teacher,
                    c["slot"],
                    date,
                    current_assignments,
                    rules,
                    student_slots=student_slots,
                    subject=subject,
                ),
            }
        )
    ranked.sort(key=lambda x: (-x["match_score"], x["teacher_id"], x["slot"]))
    return ranked


def pick_best_candidate(
    student_id: int,
    subject: str,
    teacher_list: list[Teacher],
    current_assignments: list[dict],
    date: str,
    rules: MatchRules | None = None,
    all_assignments: list[dict] | None = None,
    student_slots: dict[int, str] | None = None,
) -> dict | None:
    if student_slots is None:
        student_slots = load_student_slots(student_id, date)
    candidates = get_assignment_candidates(
        student_id,
        subject,
        teacher_list,
        current_assignments,
        date,
        rules=rules,
        all_assignments=all_assignments,
        student_slots=student_slots,
    )
    if not candidates:
        return None
    ranked = rank_candidates(
        candidates,
        teacher_list,
        date,
        current_assignments,
        rules,
        student_slots=student_slots,
        subject=subject,
    )
    return ranked[0]


def validate_assignment(
    student_id: int,
    subject: str,
    teacher_id: int,
    slot: int,
    date: str,
    teacher_list: list[Teacher],
    current_assignments: list[dict],
    rules: MatchRules | None = None,
    all_assignments: list[dict] | None = None,
    student_slots: dict[int, str] | None = None,
) -> str | None:
    """割当可能なら None、不可なら理由文字列。"""
    rules = rules or MatchRules()
    teacher = next((t for t in teacher_list if t.id == teacher_id), None)
    if teacher is None:
        return "講師が見つかりません"

    if student_slots is None:
        student_slots = load_student_slots(student_id, date)
    slot_symbol = student_slots.get(slot, "")
    block = student_slot_block_reason(slot_symbol, subject)
    if block:
        return block

    candidates = get_assignment_candidates(
        student_id,
        subject,
        [teacher],
        current_assignments,
        date,
        rules=rules,
        all_assignments=all_assignments,
        student_slots=student_slots,
    )
    ok = any(c["teacher_id"] == teacher_id and c["slot"] == slot for c in candidates)
    if ok:
        return None

    if exceeds_weekly_limit(
        student_id, subject, date, all_assignments or current_assignments, rules
    ):
        limit = weekly_limit_for(subject, rules)
        return f"{subject}は週{limit}コマまでです"

    if rules.no_teacher_gaps and would_create_teacher_gap(
        teacher_id, slot, date, teacher.slots, current_assignments
    ):
        return "空きコマが途中に残ります（空きコマなしルール）"

    if would_violate_student_consecutive_limit(
        student_id, slot, date, current_assignments
    ):
        return "生徒は3コマ連続の受講はできません"

    if would_violate_teacher_consecutive_limit(
        teacher_id, slot, date, teacher.slots, current_assignments
    ):
        return "講師は4コマ連続の担当はできません"

    return "このコマには割当できません"
