from copy import deepcopy

from fastapi import HTTPException

from schemas.assignment import AssignmentRecord
from services.assignment_store import (
    add_assignment,
    get_assignment_requests_for_date,
    get_assignments_for_date,
    remove_assignment_at_slot,
)
from services.availability_dashboard import build_availability_dashboard
from services.dashboard_builder import build_shift_dashboard_base_only
from services.slot_timing import generate_time_slots


def _teacher_name_map(iso_date: str) -> dict[int, str]:
    base = build_shift_dashboard_base_only(iso_date)
    return {t["id"]: t["name"] for t in base.get("teachers", [])}


def build_assignment_grid(iso_date: str) -> dict:
    availability = build_availability_dashboard(iso_date)
    assignments = get_assignments_for_date(iso_date)
    pending_requests = get_assignment_requests_for_date(iso_date)

    assignment_by_teacher_slot: dict[tuple[int, int], dict] = {}
    for row in assignments:
        assignment_by_teacher_slot[(row["teacher_id"], row["slot"])] = row

    teachers = []
    for t in availability.get("teachers", []):
        slots = []
        for slot_num in range(1, 5):
            avail = t.get(f"s{slot_num}", "")
            assign = assignment_by_teacher_slot.get((t["id"], slot_num))
            slots.append(
                {
                    "slot": slot_num,
                    "availability": avail,
                    "assignable": avail == "",
                    "assignment": assign,
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
        "assignments": deepcopy(assignments),
        "pending_requests": deepcopy(pending_requests),
    }


def manual_assign(
    iso_date: str,
    student_id: int,
    student_name: str,
    subject: str,
    teacher_id: int,
    slot: int,
) -> dict:
    grid = build_assignment_grid(iso_date)
    teacher_row = next((t for t in grid["teachers"] if t["id"] == teacher_id), None)
    if teacher_row is None:
        raise HTTPException(status_code=404, detail=f"Teacher id={teacher_id} not found")

    slot_info = next((s for s in teacher_row["slots"] if s["slot"] == slot), None)
    if slot_info is None or not slot_info["assignable"]:
        raise HTTPException(status_code=409, detail="このコマには割当できません（◎ または ×）")

    names = _teacher_name_map(iso_date)
    teacher_name = names.get(teacher_id, f"講師{teacher_id}")

    existing = get_assignments_for_date(iso_date)
    for row in existing:
        if row["teacher_id"] == teacher_id and row["slot"] == slot:
            remove_assignment_at_slot(iso_date, teacher_id, slot)
        if row["student_id"] == student_id and row["slot"] == slot:
            remove_assignment_at_slot(iso_date, row["teacher_id"], row["slot"])

    record = AssignmentRecord(
        date=iso_date,
        student_id=student_id,
        student_name=student_name,
        subject=subject,
        teacher_id=teacher_id,
        teacher_name=teacher_name,
        slot=slot,
    )
    add_assignment(record)
    return build_assignment_grid(iso_date)
