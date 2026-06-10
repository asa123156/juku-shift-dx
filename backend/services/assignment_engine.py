from dataclasses import dataclass

SLOTS = (1, 2, 3, 4)
BLOCKED_TEACHER_STATUSES = frozenset({"不可", "通常授業", "×", "◎"})


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


def has_consecutive_subject(
    student_id: int,
    subject: str,
    slot: int,
    current_assignments: list[dict],
    date: str,
) -> bool:
    """生徒が同じ科目を隣接コマで連続受講することになるか"""
    for adjacent in (slot - 1, slot + 1):
        if adjacent not in SLOTS:
            continue
        for assignment in current_assignments:
            if (
                assignment["date"] == date
                and assignment["student_id"] == student_id
                and assignment["slot"] == adjacent
                and assignment["subject"] == subject
            ):
                return True
    return False


def is_three_consecutive_for_teacher(
    teacher_id: int,
    slot: int,
    current_assignments: list[dict],
    date: str,
) -> bool:
    """講師がこのコマを担当すると3コマ連続になるか"""
    teacher_slots = {
        a["slot"]
        for a in current_assignments
        if a["date"] == date and a["teacher_id"] == teacher_id
    }
    teacher_slots.add(slot)

    for start in SLOTS[:2]:  # 1-2-3, 2-3-4 の連続パターン
        triple = {start, start + 1, start + 2}
        if triple.issubset(teacher_slots):
            return True
    return False


def is_teacher_slot_occupied(
    teacher_id: int,
    slot: int,
    current_assignments: list[dict],
    date: str,
) -> bool:
    return any(
        a["date"] == date and a["teacher_id"] == teacher_id and a["slot"] == slot
        for a in current_assignments
    )


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
) -> list[dict]:
    """
    全講師×全コマの組み合わせから、NGルールを通過した候補を返す。
    """
    valid_candidates: list[dict] = []

    for teacher in teacher_list:
        for slot in SLOTS:
            if teacher.slots.get(slot) in BLOCKED_TEACHER_STATUSES:
                continue

            if is_teacher_slot_occupied(teacher.id, slot, current_assignments, date):
                continue

            if is_student_slot_occupied(student_id, slot, current_assignments, date):
                continue

            if has_consecutive_subject(student_id, subject, slot, current_assignments, date):
                continue

            if is_three_consecutive_for_teacher(teacher.id, slot, current_assignments, date):
                continue

            valid_candidates.append(
                {
                    "teacher_id": teacher.id,
                    "teacher_name": teacher.name,
                    "slot": slot,
                }
            )

    return valid_candidates


def score_candidate(teacher: Teacher, slot: int) -> int:
    """空きコマほど高スコア。"""
    status = teacher.slots.get(slot, "")
    if status == "":
        return 90
    return 60


def rank_candidates(
    candidates: list[dict],
    teacher_list: list[Teacher],
) -> list[dict]:
    teacher_map = {t.id: t for t in teacher_list}
    ranked = []
    for c in candidates:
        teacher = teacher_map[c["teacher_id"]]
        ranked.append({**c, "match_score": score_candidate(teacher, c["slot"])})
    ranked.sort(key=lambda x: (-x["match_score"], x["teacher_id"], x["slot"]))
    return ranked


def pick_best_candidate(
    student_id: int,
    subject: str,
    teacher_list: list[Teacher],
    current_assignments: list[dict],
    date: str,
) -> dict | None:
    candidates = get_assignment_candidates(
        student_id, subject, teacher_list, current_assignments, date
    )
    if not candidates:
        return None
    ranked = rank_candidates(candidates, teacher_list)
    return ranked[0]
