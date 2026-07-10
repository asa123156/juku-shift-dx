from datetime import date

from fastapi import HTTPException

from schemas.period import PeriodStatus, ScheduleDay, empty_slots
from services.academic_calendar import open_dates_for_calendar_month
from services.assignment_store import get_assignments_for_date
from services.class_schedule_store import get_fixed_slots_for_entity
from services.period_store import (
    find_period_for_date,
    get_period,
    open_dates_for_period,
)
from services.schedule_publish_store import (
    is_schedule_published,
    is_schedule_request_published,
    is_teacher_schedule_published,
    is_teacher_schedule_request_published,
)
from services.shift_store import get_teacher_submission, save_teacher_bulk
from services.submission_store import is_entity_fully_submitted
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
                "is_fixed": bool(row.get("is_fixed") or row.get("lesson_kind") == "通常"),
            }
        )
    return sorted(lessons, key=lambda x: x["slot"])


def _teacher_slot_lanes_for_day(
    entity_id: int,
    iso_date: str,
    merged_slots: dict[str, str],
    show: bool,
) -> list[dict]:
    from services.teacher_slot_lanes import MAX_TEACHER_LANES, build_teacher_lanes

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
                "lanes": build_teacher_lanes(avail, by_slot.get(slot_num, []), max_lanes=MAX_TEACHER_LANES),
            }
        )
    return result


def _entity_has_assignments(role: str, entity_id: int, iso_date: str) -> bool:
    id_key = "student_id" if role == "student" else "teacher_id"
    return any(row[id_key] == entity_id for row in get_assignments_for_date(iso_date))


def _merge_day(
    role: str,
    entity_id: int,
    period_id: int,
    iso_date: str,
    readonly: bool,
    period_status: PeriodStatus,
    schedule_published: bool = False,
    schedule_requested: bool = False,
    *,
    force_show_lessons: bool = False,
) -> ScheduleDay:
    fixed_slots = get_fixed_slots_for_entity(period_id, role, entity_id, iso_date)
    if role == "teacher":
        submitted = get_teacher_submission(entity_id, iso_date)
    else:
        submitted = get_student_submission(entity_id, iso_date)

    merged: dict[str, str] = empty_slots()  # type: ignore[assignment]
    locked: dict[str, bool] = {}
    for key in SLOT_KEYS:
        if key in fixed_slots:
            locked[key] = True
            if submitted is not None and submitted[key] in ("", "×"):
                merged[key] = submitted[key]
            else:
                merged[key] = ""
        elif submitted is not None:
            val = submitted[key]
            merged[key] = val if val in ("", "×") else ""
            locked[key] = False
        else:
            merged[key] = ""
            locked[key] = False

    show_lessons = force_show_lessons or (
        period_status == "FINALIZED"
        or schedule_published
        or schedule_requested
    )
    confirmed = _confirmed_lessons(role, entity_id, iso_date, show=show_lessons)
    if schedule_requested and not schedule_published:
        for lesson in confirmed:
            key = str(lesson["slot"])
            is_regular = lesson.get("is_fixed") or lesson.get("lesson_kind") == "通常"
            if not is_regular:
                locked[key] = True
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
    fixed_slots = get_fixed_slots_for_entity(period_id, role, entity_id, iso_date)
    if role == "teacher":
        submitted = get_teacher_submission(entity_id, iso_date)
    else:
        submitted = get_student_submission(entity_id, iso_date)

    merged: dict[str, str] = empty_slots()  # type: ignore[assignment]
    for key in SLOT_KEYS:
        if key in fixed_slots:
            merged[key] = "通常授業"
        elif submitted is not None:
            merged[key] = submitted[key] if submitted[key] in ("", "×") else ""
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


def assert_proposal_received(role: str, entity_id: int, period_id: int) -> None:
    """初回提案書送付前は提出不可（講習期間のみ）。"""
    period = get_period(period_id)
    if getattr(period, "period_kind", "CRAM") == "REGULAR":
        return
    if role == "student" and not is_schedule_request_published(period_id, entity_id):
        raise HTTPException(status_code=409, detail="提案書が届くまで提出できません")
    if role == "teacher" and not is_teacher_schedule_request_published(period_id, entity_id):
        raise HTTPException(status_code=409, detail="提案書が届くまで提出できません")


def assert_entity_editable(role: str, entity_id: int, period_id: int) -> None:
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
    assert_proposal_received(role, entity_id, period_id)
    period = get_period(period_id)
    allowed_dates = set(open_dates_for_period(period))

    validated: list[dict] = []
    for row in submissions:
        iso_date = row["date"]
        if iso_date not in allowed_dates:
            raise HTTPException(status_code=400, detail=f"Date {iso_date} is outside period range")
        fixed_slots = get_fixed_slots_for_entity(period_id, role, entity_id, iso_date)
        if role == "teacher":
            existing = get_teacher_submission(entity_id, iso_date)
        else:
            existing = get_student_submission(entity_id, iso_date)
        slots: dict[str, str] = empty_slots()  # type: ignore[assignment]
        for key in SLOT_KEYS:
            if key in fixed_slots:
                prev = (existing or {}).get(key, "")
                slots[key] = prev if prev in ("", "×") else ""
                continue
            val = row["slots"][key]
            if val == "◎":
                raise HTTPException(
                    status_code=400,
                    detail=f"通常授業のコマ（{key}）は時間割表で管理されます。空きまたは × のみ提出できます",
                )
            if role == "student":
                slots[key] = validate_student_slot(val, None)
            else:
                if val not in ("×", ""):
                    raise HTTPException(status_code=400, detail=f"Invalid symbol on slot {key}")
                slots[key] = val
        validated.append({"date": iso_date, "slots": slots})

    if role == "teacher":
        return save_teacher_bulk(entity_id, validated)
    return save_student_bulk(entity_id, validated)


def _open_dates_for_schedule(
    period,
    *,
    calendar_year: int | None = None,
    month: int | None = None,
) -> list[str]:
    if getattr(period, "period_kind", "CRAM") == "REGULAR" and calendar_year is not None and month is not None:
        return open_dates_for_calendar_month(calendar_year, month, period.closed_dates)
    return open_dates_for_period(period)


def build_my_schedule(
    role: str,
    entity_id: int,
    period_id: int,
    *,
    calendar_year: int | None = None,
    month: int | None = None,
) -> dict:
    period = get_period(period_id)
    is_regular = getattr(period, "period_kind", "CRAM") == "REGULAR"
    if is_regular and (calendar_year is None or month is None):
        today = date.today()
        calendar_year = calendar_year or today.year
        month = month or today.month
    requested = False
    if is_regular:
        published = False
        readonly = period.status == "FINALIZED"
    elif role == "student":
        published = is_schedule_published(period_id, entity_id)
        requested = is_schedule_request_published(period_id, entity_id)
        readonly = period.status == "FINALIZED" or published
    else:
        published = is_teacher_schedule_published(period_id, entity_id)
        requested = is_teacher_schedule_request_published(period_id, entity_id)
        readonly = period.status == "FINALIZED" or published
    open_dates = _open_dates_for_schedule(
        period,
        calendar_year=calendar_year,
        month=month,
    )
    submission_complete = is_entity_fully_submitted(role, entity_id, open_dates)
    from services.change_request_store import has_pending_resubmit

    resubmit_pending = has_pending_resubmit(period_id, role, entity_id)
    dates = [
        _merge_day(
            role,
            entity_id,
            period_id,
            iso_date,
            readonly,
            period.status,
            schedule_published=published,
            schedule_requested=requested,
            force_show_lessons=is_regular,
        ).model_dump()
        for iso_date in open_dates
    ]
    message = None
    if readonly:
        if published and period.status != "FINALIZED":
            message = "担当者がスケジュールを確定しました。以下が確定スケジュールです。"
        else:
            message = "シフトが確定しました。以下が確定スケジュールです。"
        message += " 変更が必要な場合は変更申請を行ってください。"
    elif is_regular and period.status == "COLLECTING":
        message = (
            "通常授業の時間割です。通常授業のコマは変更できません。"
            "それ以外のコマで、空き（都合がつく）または ×（都合がつかない）を選んで提出できます。"
        )
    elif role == "student" and period.status == "COLLECTING":
        if requested and not published:
            message = (
                "講習の日程提案書です。通常授業と割当済みの講習枠は変更できません。"
                "それ以外のコマで、空き（都合がつく）または ×（都合がつかない）を選んで提出してください。"
            )
        else:
            message = "教室長から提案書が届くまでお待ちください。"
    elif role == "teacher" and period.status == "COLLECTING":
        if requested and not published:
            message = (
                "講習の日程提案書です。通常授業と割当済みの講習枠は変更できません。"
                "それ以外のコマで、空き（都合がつく）または ×（都合がつかない）を選んで提出してください。"
            )
        else:
            message = "教室長から提案書が届くまでお待ちください。"
    subject_plans: list[dict] = []
    if role == "student" and not is_regular:
        subject_plans = list_plans_for_student(period_id, entity_id)
    return {
        "role": role,
        "entity_id": entity_id,
        "period_id": period_id,
        "period_name": period.name,
        "period_start_date": period.start_date,
        "period_end_date": period.end_date,
        "period_status": period.status,
        "period_kind": getattr(period, "period_kind", "CRAM"),
        "submission_deadline": getattr(period, "submission_deadline", None),
        "schedule_requested": requested,
        "schedule_published": published,
        "submission_complete": submission_complete,
        "resubmit_pending": resubmit_pending,
        "readonly": readonly,
        "time_slots": generate_time_slots(),
        "subject_plans": subject_plans,
        "message": message,
        "dates": dates,
        "calendar_year": calendar_year,
        "month": month,
    }


def get_active_period_context(iso_date: str) -> tuple[int, PeriodStatus] | None:
    period = find_period_for_date(iso_date)
    if period is None:
        return None
    return period.id, period.status
