from copy import deepcopy

from fastapi import HTTPException

from schemas.assignment import AssignmentRecord
from services.assignment_store import (
    add_assignment,
    get_assignments_for_date,
    remove_assignment_at_slot,
)
from services.period_store import find_period_for_date
from services.schedule_context import resolve_grid_period_ids
from services.schedule_canonical import derive_unassigned_for_date
from schemas.period import empty_slots
from services.teacher_slot_lanes import build_teacher_lanes, teacher_slot_assignable
from services.slot_capacity_store import (
    DEFAULT_MAX_LANES,
    get_capacity_map_for_date,
    lesson_format_label,
    set_max_lanes as persist_max_lanes,
)
from services.assignment_engine import teachers_from_dashboard, validate_assignment
from services.availability_dashboard import build_availability_dashboard
from services.match_rules import MatchRules
from services.dashboard_builder import build_shift_dashboard_base_only
from services.entity_store import get_student_name_map
from services.slot_timing import SLOT_NUMS, generate_time_slots
from services.submission_store import get_submissions_for_date


def _teacher_name_map(iso_date: str) -> dict[int, str]:
    base = build_shift_dashboard_base_only(iso_date)
    return {t["id"]: t["name"] for t in base.get("teachers", [])}


from services.student_slot_codec import student_availability_label


def _student_availability(symbol: str) -> str:
    return student_availability_label(symbol)


def _student_name_lookup() -> dict[int, str]:
    return get_student_name_map()


def _build_student_sheets(iso_date: str, assignments: list[dict], pending_requests: list[dict]) -> list[dict]:
    submissions = get_submissions_for_date("student", iso_date)
    known_names = _student_name_lookup()
    student_names: dict[int, str] = {}
    for row in pending_requests:
        student_names[row["student_id"]] = row["student_name"]
    for row in assignments:
        student_names[row["student_id"]] = row["student_name"]
    for sid in submissions:
        student_names.setdefault(sid, known_names.get(sid, f"生徒{sid}"))

    assignment_by_student_slot: dict[tuple[int, int], dict] = {}
    for row in assignments:
        assignment_by_student_slot[(row["student_id"], row["slot"])] = row

    pending_by_student: dict[int, list[str]] = {}
    for row in pending_requests:
        pending_by_student.setdefault(row["student_id"], [])
        if row["subject"] not in pending_by_student[row["student_id"]]:
            pending_by_student[row["student_id"]].append(row["subject"])

    students: list[dict] = []
    for sid in sorted(student_names):
        subs = submissions.get(sid, empty_slots())
        slots = []
        for slot_num in SLOT_NUMS:
            symbol = subs.get(str(slot_num), "")
            slots.append(
                {
                    "slot": slot_num,
                    "availability": _student_availability(symbol),
                    "assignment": assignment_by_student_slot.get((sid, slot_num)),
                }
            )
        students.append(
            {
                "id": sid,
                "name": student_names[sid],
                "slots": slots,
                "pending_subjects": pending_by_student.get(sid, []),
            }
        )
    return students


def build_assignment_grid(iso_date: str) -> dict:
    availability = build_availability_dashboard(iso_date)
    assignments = get_assignments_for_date(iso_date)
    period = find_period_for_date(iso_date)
    if period is not None:
        pending_requests = derive_unassigned_for_date(period.id, iso_date)
    else:
        pending_requests = []
    capacity_map = get_capacity_map_for_date(iso_date)

    assignment_by_teacher_slot: dict[tuple[int, int], list[dict]] = {}
    for row in assignments:
        key = (row["teacher_id"], row["slot"])
        assignment_by_teacher_slot.setdefault(key, []).append(row)

    teachers = []
    for t in availability.get("teachers", []):
        slots = []
        for slot_num in SLOT_NUMS:
            avail = t.get(f"s{slot_num}", "")
            at_slot = assignment_by_teacher_slot.get((t["id"], slot_num), [])
            max_lanes = capacity_map.get((t["id"], slot_num), DEFAULT_MAX_LANES)
            lanes = build_teacher_lanes(avail, at_slot, max_lanes=max_lanes)
            slots.append(
                {
                    "slot": slot_num,
                    "availability": avail,
                    "assignable": teacher_slot_assignable(avail, at_slot, max_lanes=max_lanes),
                    "max_lanes": max_lanes,
                    "lesson_format": lesson_format_label(max_lanes),
                    "lanes": lanes,
                    "assignments": at_slot,
                    "assignment": at_slot[0] if at_slot else None,
                }
            )
        teachers.append(
            {
                "id": t["id"],
                "name": t["name"],
                "color": t.get("color", ""),
                "slots": slots,
            }
        )

    return {
        "date": iso_date,
        "time_slots": generate_time_slots(),
        "teachers": teachers,
        "students": _build_student_sheets(iso_date, assignments, pending_requests),
        "assignments": deepcopy(assignments),
        "pending_requests": deepcopy(pending_requests),
        "period_context": resolve_grid_period_ids(iso_date),
    }


def manual_assign(
    iso_date: str,
    student_id: int,
    student_name: str,
    subject: str,
    teacher_id: int,
    slot: int,
    rules: MatchRules | None = None,
    all_assignments: list[dict] | None = None,
    *,
    skip_rules: bool = False,
    is_fixed: bool = False,
    period_id: int | None = None,
    lesson_type: str | None = None,
) -> dict:
    # 「その他」（体験・振替など）: 通常授業と同じ固定枠扱いだが、単発予定なので毎週展開しない
    other_type = (lesson_type or "").strip() or None
    if other_type:
        is_fixed = True
    grid = build_assignment_grid(iso_date)
    teacher_row = next((t for t in grid["teachers"] if t["id"] == teacher_id), None)
    if teacher_row is None:
        raise HTTPException(status_code=404, detail=f"Teacher id={teacher_id} not found")

    slot_info = next((s for s in teacher_row["slots"] if s["slot"] == slot), None)
    if slot_info is None or not slot_info["assignable"]:
        raise HTTPException(status_code=409, detail="このコマには割当できません（空きレーンがありません）")

    existing = get_assignments_for_date(iso_date)
    preferred_teacher_id = None
    if period_id is not None:
        from services.student_plan_store import get_preferred_teacher_id

        preferred_teacher_id = get_preferred_teacher_id(period_id, student_id, subject)
    if not skip_rules:
        rules = rules or MatchRules()
        dashboard = build_availability_dashboard(iso_date)
        teacher_list = teachers_from_dashboard(dashboard)
        pool = all_assignments if all_assignments is not None else existing
        err = validate_assignment(
            student_id,
            subject,
            teacher_id,
            slot,
            iso_date,
            teacher_list,
            existing,
            rules=rules,
            all_assignments=pool,
            preferred_teacher_id=preferred_teacher_id,
        )
        if err:
            raise HTTPException(status_code=409, detail=err)

    names = _teacher_name_map(iso_date)
    teacher_name = names.get(teacher_id, f"講師{teacher_id}")

    for row in existing:
        if row["student_id"] == student_id and row["slot"] == slot:
            remove_assignment_at_slot(
                iso_date, row["teacher_id"], row["slot"], student_id=student_id
            )

    if is_fixed and not subject.strip():
        subject = other_type or "通常"

    from services.fiscal_year_store import resolve_schedule_period_for_date
    from services.schedule_context import tutoring_period_id_for_date

    regular_period = resolve_schedule_period_for_date(iso_date)
    if is_fixed:
        period_id = regular_period.id
    elif period_id is not None:
        period_id = tutoring_period_id_for_date(iso_date, period_id)
    else:
        period_id = tutoring_period_id_for_date(iso_date, regular_period.id)

    record = AssignmentRecord(
        date=iso_date,
        student_id=student_id,
        student_name=student_name,
        subject=subject.strip() or "通常",
        teacher_id=teacher_id,
        teacher_name=teacher_name,
        slot=slot,
        lesson_kind="通常" if is_fixed else "講習",
        is_fixed=is_fixed,
        lesson_type=other_type,
    )
    if skip_rules or is_fixed:
        from services.class_schedule_store import add_fixed_schedule_with_weekly_repeat, add_schedule

        if is_fixed and period_id is not None and other_type is None:
            add_fixed_schedule_with_weekly_repeat(record, period_id=period_id, source="manual")
        else:
            add_schedule(record, period_id=period_id, is_fixed=is_fixed, source="manual")
    else:
        add_assignment(record)
    return build_assignment_grid(iso_date)


def update_slot_capacity(
    iso_date: str,
    teacher_id: int,
    slot: int,
    max_lanes: int,
) -> dict:
    grid = build_assignment_grid(iso_date)
    teacher_row = next((t for t in grid["teachers"] if t["id"] == teacher_id), None)
    if teacher_row is None:
        raise HTTPException(status_code=404, detail=f"Teacher id={teacher_id} not found")
    slot_info = next((s for s in teacher_row["slots"] if s["slot"] == slot), None)
    if slot_info is None:
        raise HTTPException(status_code=404, detail=f"Slot {slot} not found")
    persist_max_lanes(
        teacher_id,
        iso_date,
        slot,
        max_lanes,
        avail=slot_info["availability"],
        assignments=slot_info.get("assignments") or [],
    )
    return build_assignment_grid(iso_date)
