from fastapi import HTTPException

from schemas.period import PeriodStatus, ScheduleDay, SlotSymbol, empty_slots
from services.assignment_store import get_assignments_for_date
from services.period_store import (
    find_period_for_date,
    get_entity_base_day,
    get_period,
    iter_dates,
)
from services.shift_store import get_teacher_submission, save_teacher_bulk
from services.slot_timing import generate_time_slots
from services.student_store import get_student_submission, save_student_bulk


def _confirmed_lessons(student_id: int, iso_date: str, finalized: bool) -> list[dict]:
    if not finalized:
        return []
    lessons = []
    for row in get_assignments_for_date(iso_date):
        if row["student_id"] != student_id:
            continue
        lessons.append(
            {
                "slot": row["slot"],
                "teacher_name": row["teacher_name"],
                "subject": row["subject"],
            }
        )
    return sorted(lessons, key=lambda x: x["slot"])


def _merge_day(
    role: str,
    entity_id: int,
    period_id: int,
    iso_date: str,
    readonly: bool,
    period_status: PeriodStatus,
) -> ScheduleDay:
    base = get_entity_base_day(period_id, role, entity_id, iso_date)
    if role == "teacher":
        submitted = get_teacher_submission(entity_id, iso_date)
    else:
        submitted = get_student_submission(entity_id, iso_date)

    show_fixed = period_status == "FINALIZED"
    merged: dict[str, SlotSymbol] = empty_slots()
    locked: dict[str, bool] = {}
    for key in ("1", "2", "3", "4"):
        if show_fixed and base[key] == "◎":
            merged[key] = "◎"
            locked[key] = True
        elif submitted is not None:
            merged[key] = submitted[key]
            locked[key] = False
        else:
            merged[key] = base[key] if show_fixed else ""
            locked[key] = False

    confirmed = _confirmed_lessons(entity_id, iso_date, finalized=show_fixed and role == "student")
    return ScheduleDay(
        date=iso_date,
        slots=merged,
        locked_slots=locked,
        readonly=readonly,
        confirmed_lessons=confirmed,
    )


def build_merged_slots_for_export(
    role: str,
    entity_id: int,
    period_id: int,
    iso_date: str,
) -> dict[str, SlotSymbol]:
    period = get_period(period_id)
    base = get_entity_base_day(period_id, role, entity_id, iso_date)
    if role == "teacher":
        submitted = get_teacher_submission(entity_id, iso_date)
    else:
        submitted = get_student_submission(entity_id, iso_date)

    merged: dict[str, SlotSymbol] = empty_slots()
    for key in ("1", "2", "3", "4"):
        if period.status == "FINALIZED" and base[key] == "◎":
            merged[key] = "◎"
        elif submitted is not None:
            merged[key] = submitted[key]
        else:
            merged[key] = ""
    return merged


def assert_period_collecting(period_id: int) -> None:
    period = get_period(period_id)
    if period.status != "COLLECTING":
        raise HTTPException(
            status_code=409,
            detail=f"Period id={period_id} is {period.status}; submissions only allowed in COLLECTING",
        )


def bulk_save_submissions(
    role: str,
    entity_id: int,
    period_id: int,
    submissions: list[dict],
) -> list[str]:
    period = get_period(period_id)
    assert_period_collecting(period_id)
    allowed_dates = set(iter_dates(period.start_date, period.end_date))

    validated: list[dict] = []
    for row in submissions:
        iso_date = row["date"]
        if iso_date not in allowed_dates:
            raise HTTPException(status_code=400, detail=f"Date {iso_date} is outside period range")
        base = get_entity_base_day(period_id, role, entity_id, iso_date)
        slots: dict[str, SlotSymbol] = empty_slots()
        for key in ("1", "2", "3", "4"):
            if base[key] == "◎":
                slots[key] = "◎"
            else:
                val = row["slots"][key]
                if val == "◎":
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot set ◎ on slot {key} for {iso_date}; fixed by admin",
                    )
                if val not in ("×", ""):
                    raise HTTPException(status_code=400, detail=f"Invalid symbol on slot {key}")
                slots[key] = val
        validated.append({"date": iso_date, "slots": slots})

    if role == "teacher":
        return save_teacher_bulk(entity_id, validated)
    return save_student_bulk(entity_id, validated)


def build_my_schedule(role: str, entity_id: int, period_id: int) -> dict:
    period = get_period(period_id)
    readonly = period.status == "FINALIZED"
    dates = [
        _merge_day(role, entity_id, period_id, iso_date, readonly, period.status).model_dump()
        for iso_date in iter_dates(period.start_date, period.end_date)
    ]
    message = None
    if readonly and role == "student":
        message = "シフトが確定しました。以下が確定スケジュールです。"
    return {
        "role": role,
        "entity_id": entity_id,
        "period_id": period_id,
        "period_name": period.name,
        "period_status": period.status,
        "readonly": readonly,
        "time_slots": generate_time_slots(),
        "message": message,
        "dates": dates,
    }


def get_active_period_context(iso_date: str) -> tuple[int, PeriodStatus] | None:
    period = find_period_for_date(iso_date)
    if period is None:
        return None
    return period.id, period.status
