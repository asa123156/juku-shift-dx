"""時間割表（assignments）を正本とした未割当・提案データの算出。"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from services.assignment_store import get_assignments_between
from services.entity_store import get_student, get_student_name_map, list_students
from services.period_store import get_period, open_dates_for_period
from services.student_plan_store import list_plans_for_period


def _is_tutoring_assignment(row: dict) -> bool:
    if "is_fixed" in row:
        return not row["is_fixed"]
    return (row.get("lesson_kind") or "講習") != "通常"


def count_assignments_by_subject(assignments: list[dict], student_id: int) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in assignments:
        if row["student_id"] != student_id or not _is_tutoring_assignment(row):
            continue
        counts[row["subject"]] += 1
    return dict(counts)


def compute_student_pending_count(
    student_id: int,
    plans: list[dict],
    assignments: list[dict],
) -> int:
    """希望コマ数 − 時間割表の割当数（教科ごと）。"""
    if not plans:
        return 0
    assigned = count_assignments_by_subject(assignments, student_id)
    pending = 0
    for plan in plans:
        need = int(plan.get("slot_count") or 0)
        have = assigned.get(plan["subject"], 0)
        pending += max(0, need - have)
    return pending


def compute_pending_subjects(
    student_id: int,
    plans: list[dict],
    assignments: list[dict],
) -> list[str]:
    assigned = count_assignments_by_subject(assignments, student_id)
    pending: list[str] = []
    for plan in plans:
        need = int(plan.get("slot_count") or 0)
        have = assigned.get(plan["subject"], 0)
        remaining = max(0, need - have)
        pending.extend([plan["subject"]] * remaining)
    return pending


def derive_pending_requests(period_id: int) -> list[dict]:
    """期間全体の未割当（希望コマ数 − 講習割当数）をフラットリストで返す。"""
    period = get_period(period_id)
    open_dates = open_dates_for_period(period)
    if not open_dates:
        return []

    plans_by_student = list_plans_for_period(period_id)
    all_assignments = get_assignments_between(period.start_date, period.end_date)
    tutoring = [a for a in all_assignments if _is_tutoring_assignment(a)]
    names = get_student_name_map()

    requests: list[dict] = []
    for sid, plans in plans_by_student.items():
        if not plans:
            continue
        assigned = count_assignments_by_subject(tutoring, sid)
        student_name = names.get(sid, f"生徒{sid}")
        for plan in plans:
            need = int(plan.get("slot_count") or 0)
            have = assigned.get(plan["subject"], 0)
            remaining = max(0, need - have)
            for _ in range(remaining):
                requests.append(
                    {
                        "student_id": sid,
                        "student_name": student_name,
                        "subject": plan["subject"],
                    }
                )
    return requests


def derive_unassigned_by_date(period_id: int) -> dict[str, list[dict]]:
    """各開校日で同じ未割当プールを参照できるよう返す（日付への事前分散なし）。"""
    open_dates = open_dates_for_period(get_period(period_id))
    pool = derive_pending_requests(period_id)
    return {iso_date: deepcopy(pool) for iso_date in open_dates}


def derive_unassigned_for_date(period_id: int, iso_date: str) -> list[dict]:
    period = get_period(period_id)
    open_dates = open_dates_for_period(period)
    if iso_date not in open_dates:
        return []
    return derive_pending_requests(period_id)


def student_assignments_for_period(period_id: int, student_id: int) -> list[dict]:
    period = get_period(period_id)
    rows = get_assignments_between(period.start_date, period.end_date)
    return sorted(
        [r for r in rows if r["student_id"] == student_id and _is_tutoring_assignment(r)],
        key=lambda x: (x["date"], x["slot"]),
    )


def student_all_assignments_for_period(period_id: int, student_id: int) -> list[dict]:
    """提案書用: 通常授業（is_fixed）と講習枠の両方。"""
    period = get_period(period_id)
    rows = get_assignments_between(period.start_date, period.end_date)
    return sorted(
        [r for r in rows if r["student_id"] == student_id],
        key=lambda x: (x["date"], x["slot"]),
    )


def _proposal_row_from_assignment(assign: dict, time_by_slot: dict) -> dict:
    ts = time_by_slot.get(assign["slot"], {})
    is_regular = assign.get("is_fixed") or (assign.get("lesson_kind") or "講習") == "通常"
    return {
        "date": assign["date"],
        "slot": assign["slot"],
        "start": ts.get("start", ""),
        "end": ts.get("end", ""),
        "subject": "通常授業" if is_regular else assign["subject"],
        "teacher_name": assign["teacher_name"],
        "lesson_kind": "通常" if is_regular else (assign.get("lesson_kind") or "講習"),
    }


def build_student_proposal_rows(period_id: int, student_id: int) -> dict:
    """提案書用: 時間割表から生徒の割当行を返す（通常授業含む）。"""
    from services.slot_capacity_store import get_max_lanes
    from services.slot_timing import generate_time_slots

    period = get_period(period_id)
    student = get_student(student_id)
    time_by_slot = {ts["slot"]: ts for ts in generate_time_slots()}
    rows: list[dict] = []
    for assign in student_all_assignments_for_period(period_id, student_id):
        is_regular = assign.get("is_fixed") or (assign.get("lesson_kind") or "講習") == "通常"
        repeat = 1
        if is_regular and get_max_lanes(assign["teacher_id"], assign["date"], assign["slot"]) >= 4:
            repeat = 2
        row = _proposal_row_from_assignment(assign, time_by_slot)
        for _ in range(repeat):
            rows.append(dict(row))
    return {
        "period_id": period_id,
        "period_name": period.name,
        "student_id": student_id,
        "student_name": student["name"],
        "grade_label": student.get("grade_label", ""),
        "rows": rows,
    }


def collect_students_with_grid_data(period_id: int) -> dict[int, str]:
    """時間割表に登場する生徒 ID → 名前。"""
    period = get_period(period_id)
    names = get_student_name_map()
    registry = {s["id"]: s["name"] for s in list_students()}
    for row in get_assignments_between(period.start_date, period.end_date):
        if _is_tutoring_assignment(row):
            registry[row["student_id"]] = row["student_name"]
    for sid, name in names.items():
        registry.setdefault(sid, name)
    return registry
