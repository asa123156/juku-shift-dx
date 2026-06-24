from fastapi import HTTPException

from schemas.period import PeriodStatus, ScheduleDay, SlotSymbol, empty_slots
from services.assignment_store import get_assignments_for_date
from services.period_store import (
    find_period_for_date,
    get_entity_base_day,
    get_period,
    open_dates_for_period,
    iter_dates,
)
from services.schedule_publish_store import (
    is_schedule_published,
    is_schedule_request_published,
    is_teacher_schedule_published,
)
from services.shift_store import get_teacher_submission, save_teacher_bulk
from services.slot_timing import SLOT_KEYS, SLOT_NUMS, generate_time_slots
from services.student_plan_store import list_plans_for_student
from services.student_slot_codec import validate_student_slot
from services.student_store import get_student_submission, save_student_bulk


def _confirmed_lessons(role: str, entity_id: int, iso_date: str, show: bool) -> list[dict]:
    if not show:
        return []
    id_key = "student_id" if role == "student" else "teacher_id"
    lessons = []
    for row in get_assignments_for_date(iso_date):
        if row[id_key] != entity_id:
            continue
        lessons.append(
            {
                "slot": row["slot"],
                "teacher_name": row["teacher_name"],
                "student_name": row["student_name"],
                "subject": row["subject"],
                "lesson_kind": row.get("lesson_kind") or "講習",
            }
        )
    return sorted(lessons, key=lambda x: x["slot"])


def _teacher_slot_lanes_for_day(
    entity_id: int,
    iso_date: str,
    merged_slots: dict[str, str],
    show: bool,
) -> list[dict]:
    from services.teacher_slot_lanes import build_teacher_lanes

    if not show:
        return []
    assignments = [
        a for a in get_assignments_for_date(iso_date) if a["teacher_id"] == entity_id
    ]
    by_slot: dict[int, list] = {}
    for row in assignments:
        by_slot.setdefault(int(row["slot"]), []).append(row)

    result: list[dict] = []
    for slot_num in SLOT_NUMS:
        avail = merged_slots.get(str(slot_num), "")
        result.append(
            {
                "slot": slot_num,
                "lanes": build_teacher_lanes(avail, by_slot.get(slot_num, [])),
            }
        )
    return result


def _merge_day(
    role: str,
    entity_id: int,
    period_id: int,
    iso_date: str,
    readonly: bool,
    period_status: PeriodStatus,
    schedule_published: bool = False,
) -> ScheduleDay:
    base = get_entity_base_day(period_id, role, entity_id, iso_date)
    if role == "teacher":
        submitted = get_teacher_submission(entity_id, iso_date)
    else:
        submitted = get_student_submission(entity_id, iso_date)

    show_fixed = period_status == "FINALIZED"
    merged: dict[str, str] = empty_slots()  # type: ignore[assignment]
    locked: dict[str, bool] = {}
    for key in SLOT_KEYS:
        student_regular = role == "student" and base[key] == "◎"
        finalized_regular = show_fixed and base[key] == "◎"
        if student_regular or finalized_regular:
            merged[key] = "◎"
            locked[key] = True
        elif submitted is not None:
            merged[key] = submitted[key]
            locked[key] = False
        else:
            merged[key] = base[key] if show_fixed else ""
            locked[key] = False

    show_lessons = show_fixed or schedule_published
    confirmed = _confirmed_lessons(role, entity_id, iso_date, show=show_lessons)
    teacher_slot_lanes = (
        _teacher_slot_lanes_for_day(entity_id, iso_date, merged, show=show_lessons)
        if role == "teacher"
        else []
    )
    return ScheduleDay(
        date=iso_date,
        slots=merged,
        locked_slots=locked,
        readonly=readonly,
        confirmed_lessons=confirmed,
        teacher_slot_lanes=teacher_slot_lanes,
    )


def build_merged_slots_for_export(
    role: str,
    entity_id: int,
    period_id: int,
    iso_date: str,
) -> dict[str, str]:
    period = get_period(period_id)
    base = get_entity_base_day(period_id, role, entity_id, iso_date)
    if role == "teacher":
        submitted = get_teacher_submission(entity_id, iso_date)
    else:
        submitted = get_student_submission(entity_id, iso_date)

    merged: dict[str, str] = empty_slots()  # type: ignore[assignment]
    for key in SLOT_KEYS:
        student_regular = role == "student" and base[key] == "◎"
        finalized_regular = period.status == "FINALIZED" and base[key] == "◎"
        if student_regular or finalized_regular:
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


def assert_entity_editable(role: str, entity_id: int, period_id: int) -> None:
    """送付済み・確定後は直接編集不可（変更申請を使う）。"""
    period = get_period(period_id)
    if period.status == "FINALIZED":
        raise HTTPException(
            status_code=409,
            detail="確定済みのため直接編集できません。変更申請を行ってください。",
        )
    if role == "student" and is_schedule_published(period_id, entity_id):
        raise HTTPException(
            status_code=409,
            detail="スケジュール送付済みのため直接編集できません。変更申請を行ってください。",
        )
    if role == "student" and not is_schedule_request_published(period_id, entity_id):
        raise HTTPException(
            status_code=409,
            detail="提案書が未送付です。教室長が初回送付後に回答してください。",
        )
    if role == "teacher" and is_teacher_schedule_published(period_id, entity_id):
        raise HTTPException(
            status_code=409,
            detail="スケジュール送付済みのため直接編集できません。変更申請を行ってください。",
        )


def bulk_save_submissions(
    role: str,
    entity_id: int,
    period_id: int,
    submissions: list[dict],
) -> list[str]:
    assert_entity_editable(role, entity_id, period_id)
    assert_period_collecting(period_id)
    period = get_period(period_id)
    allowed_dates = set(open_dates_for_period(period))
    student_subjects: set[str] | None = None
    if role == "student":
        student_subjects = {p["subject"] for p in list_plans_for_student(period_id, entity_id)}

    validated: list[dict] = []
    for row in submissions:
        iso_date = row["date"]
        if iso_date not in allowed_dates:
            raise HTTPException(status_code=400, detail=f"Date {iso_date} is outside period range")
        base = get_entity_base_day(period_id, role, entity_id, iso_date)
        slots: dict[str, str] = empty_slots()  # type: ignore[assignment]
        for key in SLOT_KEYS:
            if base[key] == "◎":
                slots[key] = "◎"
            else:
                val = row["slots"][key]
                if role == "student":
                    if val == "◎":
                        raise HTTPException(
                            status_code=400,
                            detail=f"Cannot set ◎ on slot {key} for {iso_date}; fixed by admin",
                        )
                    slots[key] = validate_student_slot(val, student_subjects)
                else:
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
    requested = False
    if role == "student":
        published = is_schedule_published(period_id, entity_id)
        requested = is_schedule_request_published(period_id, entity_id)
    else:
        published = is_teacher_schedule_published(period_id, entity_id)
    readonly = period.status == "FINALIZED" or published or (role == "student" and not requested)
    dates = [
        _merge_day(
            role, entity_id, period_id, iso_date, readonly, period.status, schedule_published=published
        ).model_dump()
        for iso_date in open_dates_for_period(period)
    ]
    message = None
    if role == "student" and period.status == "COLLECTING" and not requested and not published:
        message = "まだ提案書が送付されていません。教室長の初回送付をお待ちください。"
    elif readonly:
        if published and period.status != "FINALIZED":
            message = "担当者がスケジュールを確定しました。以下が確定スケジュールです。"
        else:
            message = "シフトが確定しました。以下が確定スケジュールです。"
        message += " 変更が必要な場合は変更申請を行ってください。"
    elif role == "student" and period.status == "COLLECTING":
        message = (
            "教室長から送付されたスケジュール表です。"
            "◎ の通常授業以外のコマで、空き（都合つく）または ×（都合つかない）を入力して提出してください。"
        )
    subject_plans: list[dict] = []
    if role == "student":
        subject_plans = list_plans_for_student(period_id, entity_id)
    return {
        "role": role,
        "entity_id": entity_id,
        "period_id": period_id,
        "period_name": period.name,
        "period_start_date": period.start_date,
        "period_end_date": period.end_date,
        "period_status": period.status,
        "schedule_requested": requested,
        "schedule_published": published,
        "readonly": readonly,
        "time_slots": generate_time_slots(),
        "subject_plans": subject_plans,
        "message": message,
        "dates": dates,
    }


def get_active_period_context(iso_date: str) -> tuple[int, PeriodStatus] | None:
    period = find_period_for_date(iso_date)
    if period is None:
        return None
    return period.id, period.status
