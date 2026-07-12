"""マッチングルール: 空きコマなし + 科目ごとの週コマ上限 + 連続コマ上限（裏ルール）。"""

from dataclasses import dataclass, field
from datetime import date

from services.slot_timing import SLOT_COUNT, SLOT_KEYS, SLOT_NUMS

SLOTS = SLOT_NUMS
BLOCKED_TEACHER_STATUSES = frozenset({"不可", "通常授業", "×", "◎"})

# 自動マッチング上、まとめて扱う教科グループ（算数→数学 / 物理・化学→理科）
MATH_SUBJECTS = frozenset({"数学", "算数", "数学I", "数学II"})
SCIENCE_SUBJECTS = frozenset({"理科", "物理", "化学"})

# 裏ルール（UI から変更不可）: この長さ以上の連続占有は不可
STUDENT_MAX_CONSECUTIVE_RUN = 3  # 生徒: 3コマ連続不可（最大2コマまで）
TEACHER_MAX_CONSECUTIVE_RUN = 4  # 講師: 4コマ連続不可（最大3コマまで）

DEFAULT_WEEKLY_LIMITS: dict[str, int] = {
    "国語": 1,
    "数学": 2,
    "英語": 0,
    "理科": 0,
    "社会": 0,
}


@dataclass
class MatchRules:
    # 生徒・講師とも授業と授業の間に空きコマを作らない（優先度ルール。
    # 満たせる候補が無い場合はルールを無視して埋める）
    no_gaps: bool = True
    weekly_limits: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_WEEKLY_LIMITS))

    @classmethod
    def from_dict(cls, data: dict | None) -> "MatchRules":
        if not data:
            return cls()
        limits = dict(DEFAULT_WEEKLY_LIMITS)
        if data.get("weekly_limits"):
            for k, v in data["weekly_limits"].items():
                limits[normalize_limit_subject(k)] = int(v)
        no_gaps = data.get("no_gaps", data.get("no_teacher_gaps", True))  # 旧キー互換
        return cls(
            no_gaps=bool(no_gaps),
            weekly_limits=limits,
        )

    def model_dump(self) -> dict:
        return {
            "no_gaps": self.no_gaps,
            "weekly_limits": dict(self.weekly_limits),
        }


def week_key(iso_date: str) -> str:
    d = date.fromisoformat(iso_date)
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def normalize_limit_subject(subject: str) -> str:
    if subject in MATH_SUBJECTS:
        return "数学"
    if subject in SCIENCE_SUBJECTS:
        return "理科"
    return subject


def _subject_group(normalized: str) -> frozenset[str] | None:
    if normalized == "数学":
        return MATH_SUBJECTS
    if normalized == "理科":
        return SCIENCE_SUBJECTS
    return None


def weekly_limit_for(subject: str, rules: MatchRules) -> int | None:
    lim = rules.weekly_limits.get(normalize_limit_subject(subject), 0)
    return lim if lim > 0 else None


def count_weekly_subject(
    student_id: int,
    subject: str,
    iso_date: str,
    all_assignments: list[dict],
) -> int:
    wk = week_key(iso_date)
    group = _subject_group(normalize_limit_subject(subject))
    subjects = group if group is not None else {subject}
    return sum(
        1
        for a in all_assignments
        if a["student_id"] == student_id
        and a["subject"] in subjects
        and week_key(a["date"]) == wk
    )


def exceeds_weekly_limit(
    student_id: int,
    subject: str,
    iso_date: str,
    all_assignments: list[dict],
    rules: MatchRules,
) -> bool:
    limit = weekly_limit_for(subject, rules)
    if limit is None:
        return False
    return count_weekly_subject(student_id, subject, iso_date, all_assignments) >= limit


def teacher_occupied_slots(
    teacher_id: int,
    iso_date: str,
    teacher_slots: dict[int, str],
    all_assignments: list[dict],
) -> set[int]:
    occupied: set[int] = set()
    for s in SLOTS:
        if teacher_slots.get(s, "") in BLOCKED_TEACHER_STATUSES:
            occupied.add(s)
    for a in all_assignments:
        if a["date"] == iso_date and a["teacher_id"] == teacher_id:
            occupied.add(a["slot"])
    return occupied


def would_create_teacher_gap(
    teacher_id: int,
    slot: int,
    iso_date: str,
    teacher_slots: dict[int, str],
    all_assignments: list[dict],
) -> bool:
    """割当後に講師スケジュールの途中に空きコマが残るか。"""
    occupied = teacher_occupied_slots(teacher_id, iso_date, teacher_slots, all_assignments)
    occupied.add(slot)
    if len(occupied) < 2:
        return False
    lo, hi = min(occupied), max(occupied)
    for s in range(lo, hi + 1):
        if s in occupied:
            continue
        if teacher_slots.get(s, "") not in BLOCKED_TEACHER_STATUSES:
            return True
    return False


def student_assigned_slots(
    student_id: int,
    iso_date: str,
    all_assignments: list[dict],
) -> set[int]:
    return {
        int(a["slot"])
        for a in all_assignments
        if a["date"] == iso_date and a["student_id"] == student_id
    }


def would_create_student_gap(
    student_id: int,
    slot: int,
    iso_date: str,
    student_slots: dict[int, str],
    all_assignments: list[dict],
) -> bool:
    """割当後に生徒スケジュールの途中に空きコマが残るか（講師版と同型）。

    通常授業（◎）は授業として占有扱い。「×」は生徒が塾に居ない枠なので
    占有にもギャップにも数えず、割当可能な空き（""）だけをギャップとみなす。
    """
    from services.student_slot_codec import parse_student_slot

    occupied = student_assigned_slots(student_id, iso_date, all_assignments)
    for s in SLOTS:
        if parse_student_slot(student_slots.get(s, ""))["kind"] == "通常授業":
            occupied.add(s)
    occupied.add(slot)
    if len(occupied) < 2:
        return False
    lo, hi = min(occupied), max(occupied)
    for s in range(lo, hi + 1):
        if s in occupied:
            continue
        if parse_student_slot(student_slots.get(s, ""))["kind"] == "空き":
            return True
    return False


def longest_consecutive_run(occupied: set[int]) -> int:
    if not occupied:
        return 0
    best = 0
    for start in SLOTS:
        if start not in occupied:
            continue
        length = 0
        s = start
        while s in occupied:
            length += 1
            s += 1
        if length > best:
            best = length
    return best


def would_exceed_consecutive_run(occupied: set[int], slot: int, forbidden_run: int) -> bool:
    """forbidden_run=3 なら 3 コマ以上の連続占有になる割当を不可とする。"""
    extended = set(occupied)
    extended.add(slot)
    return longest_consecutive_run(extended) >= forbidden_run


def would_violate_student_consecutive_limit(
    student_id: int,
    slot: int,
    iso_date: str,
    all_assignments: list[dict],
) -> bool:
    """生徒が同日に3コマ連続で受講することを防ぐ（裏ルール）。"""
    occupied = student_assigned_slots(student_id, iso_date, all_assignments)
    return would_exceed_consecutive_run(occupied, slot, STUDENT_MAX_CONSECUTIVE_RUN)


def would_violate_teacher_consecutive_limit(
    teacher_id: int,
    slot: int,
    iso_date: str,
    teacher_slots: dict[int, str],
    all_assignments: list[dict],
) -> bool:
    """講師が同日に4コマ連続で担当することを防ぐ（裏ルール）。"""
    occupied = teacher_occupied_slots(teacher_id, iso_date, teacher_slots, all_assignments)
    return would_exceed_consecutive_run(occupied, slot, TEACHER_MAX_CONSECUTIVE_RUN)
