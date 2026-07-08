"""class_schedules テーブル（時間割正本）の CRUD とスケジュール取得。"""

from __future__ import annotations

from copy import deepcopy
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal
from models import ClassSchedule as ClassScheduleRow
from schemas.assignment import AssignmentRecord
from services.period_store import find_period_for_date, get_period, open_dates_for_period
from services.slot_timing import SLOT_KEYS, SLOT_NUMS, generate_time_slots


def _session() -> Session:
    return SessionLocal()


def _resolve_period_id(iso_date: str, period_id: int | None = None) -> int:
    if period_id is not None:
        return period_id
    period = find_period_for_date(iso_date)
    if period is not None:
        return period.id
    from services.fiscal_year_store import resolve_schedule_period_for_date

    return resolve_schedule_period_for_date(iso_date).id


def row_to_dict(row: ClassScheduleRow) -> dict:
    return {
        "date": row.slot_date.isoformat(),
        "period_id": row.period_id,
        "student_id": row.student_id,
        "student_name": row.student_name,
        "subject": row.subject,
        "teacher_id": row.teacher_id,
        "teacher_name": row.teacher_name,
        "slot": row.slot,
        "is_fixed": bool(row.is_fixed),
        "lesson_kind": "通常" if row.is_fixed else "講習",
        "source": row.source,
    }


def assignment_record_to_row(
    record: AssignmentRecord,
    *,
    period_id: int | None = None,
    is_fixed: bool | None = None,
    source: str = "manual",
) -> ClassScheduleRow:
    pid = _resolve_period_id(record.date, period_id)
    fixed = is_fixed if is_fixed is not None else (record.lesson_kind == "通常")
    return ClassScheduleRow(
        period_id=pid,
        slot_date=date.fromisoformat(record.date),
        slot=record.slot,
        teacher_id=record.teacher_id,
        teacher_name=record.teacher_name,
        student_id=record.student_id,
        student_name=record.student_name,
        subject=record.subject,
        is_fixed=fixed,
        source=source,
    )


def get_schedules_between(start: str, end: str, *, fixed_only: bool | None = None) -> list[dict]:
    start_d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    with _session() as db:
        query = select(ClassScheduleRow).where(
            ClassScheduleRow.slot_date >= start_d,
            ClassScheduleRow.slot_date <= end_d,
        )
        if fixed_only is True:
            query = query.where(ClassScheduleRow.is_fixed.is_(True))
        elif fixed_only is False:
            query = query.where(ClassScheduleRow.is_fixed.is_(False))
        rows = db.scalars(query.order_by(ClassScheduleRow.id)).all()
    return deepcopy([row_to_dict(row) for row in rows])


def get_schedules_for_date(iso_date: str, *, fixed_only: bool | None = None) -> list[dict]:
    target = date.fromisoformat(iso_date)
    with _session() as db:
        query = select(ClassScheduleRow).where(ClassScheduleRow.slot_date == target)
        if fixed_only is True:
            query = query.where(ClassScheduleRow.is_fixed.is_(True))
        elif fixed_only is False:
            query = query.where(ClassScheduleRow.is_fixed.is_(False))
        rows = db.scalars(query.order_by(ClassScheduleRow.id)).all()
    return deepcopy([row_to_dict(row) for row in rows])


def get_assignments_for_date(iso_date: str) -> list[dict]:
    """互換: assignments API 向け dict（lesson_kind 付き）。"""
    return get_schedules_for_date(iso_date)


def get_assignments_between(start: str, end: str) -> list[dict]:
    return get_schedules_between(start, end)


def add_schedule(
    record: AssignmentRecord,
    *,
    period_id: int | None = None,
    is_fixed: bool | None = None,
    source: str = "manual",
) -> None:
    with _session() as db:
        db.add(assignment_record_to_row(record, period_id=period_id, is_fixed=is_fixed, source=source))
        db.commit()


def add_fixed_schedule_with_weekly_repeat(
    record: AssignmentRecord,
    *,
    period_id: int,
    source: str = "manual",
) -> list[str]:
    """通常授業を登録し、Period 内の同一曜日すべてに展開する（年度または講習期間）。"""
    period = get_period(period_id)
    anchor = date.fromisoformat(record.date)
    weekday = anchor.weekday()
    target_dates = [
        iso_date
        for iso_date in open_dates_for_period(period)
        if date.fromisoformat(iso_date).weekday() == weekday
    ]
    subject = (record.subject or "").strip() or "通常"

    with _session() as db:
        for iso_date in target_dates:
            target = date.fromisoformat(iso_date)
            db.query(ClassScheduleRow).filter(
                ClassScheduleRow.slot_date == target,
                ClassScheduleRow.student_id == record.student_id,
                ClassScheduleRow.slot == record.slot,
            ).delete(synchronize_session=False)
            db.query(ClassScheduleRow).filter(
                ClassScheduleRow.period_id == period_id,
                ClassScheduleRow.slot_date == target,
                ClassScheduleRow.teacher_id == record.teacher_id,
                ClassScheduleRow.slot == record.slot,
                ClassScheduleRow.is_fixed.is_(True),
            ).delete(synchronize_session=False)
            db.add(
                ClassScheduleRow(
                    period_id=period_id,
                    slot_date=target,
                    slot=record.slot,
                    teacher_id=record.teacher_id,
                    teacher_name=record.teacher_name,
                    student_id=record.student_id,
                    student_name=record.student_name,
                    subject=subject,
                    is_fixed=True,
                    source=source,
                )
            )
        db.commit()
    return target_dates


def add_assignment(record: AssignmentRecord) -> None:
    from services.assignment_kind import infer_lesson_kind

    fixed = record.lesson_kind == "通常" if record.lesson_kind else None
    if fixed is None:
        fixed = infer_lesson_kind(record.date, record.teacher_id, record.slot) == "通常"
    add_schedule(record, is_fixed=fixed, source="manual")


def remove_schedule_at_slot(
    iso_date: str,
    teacher_id: int,
    slot: int,
    student_id: int | None = None,
) -> None:
    target = date.fromisoformat(iso_date)
    with _session() as db:
        query = db.query(ClassScheduleRow).filter(
            ClassScheduleRow.slot_date == target,
            ClassScheduleRow.teacher_id == teacher_id,
            ClassScheduleRow.slot == slot,
        )
        if student_id is not None:
            query = query.filter(ClassScheduleRow.student_id == student_id)
        query.delete(synchronize_session=False)
        db.commit()


def remove_assignment_at_slot(
    iso_date: str,
    teacher_id: int,
    slot: int,
    student_id: int | None = None,
) -> None:
    remove_schedule_at_slot(iso_date, teacher_id, slot, student_id=student_id)


def cancel_schedule_at_slot(
    iso_date: str,
    teacher_id: int,
    slot: int,
    student_id: int | None = None,
) -> dict | None:
    target = date.fromisoformat(iso_date)
    with _session() as db:
        query = select(ClassScheduleRow).where(
            ClassScheduleRow.slot_date == target,
            ClassScheduleRow.teacher_id == teacher_id,
            ClassScheduleRow.slot == slot,
        )
        if student_id is not None:
            query = query.where(ClassScheduleRow.student_id == student_id)
        row = db.scalars(query).first()
        if row is None:
            return None
        record = row_to_dict(row)
        db.delete(row)
        db.commit()
    return record


def cancel_assignment_at_slot(
    iso_date: str,
    teacher_id: int,
    slot: int,
    student_id: int | None = None,
) -> dict | None:
    return cancel_schedule_at_slot(iso_date, teacher_id, slot, student_id=student_id)


def clear_tutoring_assignments_for_student(period_id: int, student_id: int) -> int:
    """期間内の講習割当（通常授業以外）をすべて削除する。"""
    period = get_period(period_id)
    start = date.fromisoformat(period.start_date)
    end = date.fromisoformat(period.end_date)
    with _session() as db:
        deleted = (
            db.query(ClassScheduleRow)
            .filter(
                ClassScheduleRow.period_id == period_id,
                ClassScheduleRow.student_id == student_id,
                ClassScheduleRow.is_fixed.is_(False),
                ClassScheduleRow.slot_date >= start,
                ClassScheduleRow.slot_date <= end,
            )
            .delete(synchronize_session=False)
        )
        db.commit()
    return int(deleted)


def save_schedules_for_date(
    iso_date: str,
    rows: list[dict],
    *,
    period_id: int | None = None,
    tutoring_only: bool = False,
) -> None:
    """日付単位で保存。tutoring_only=True なら is_fixed=False のみ差し替え。"""
    target = date.fromisoformat(iso_date)
    pid = _resolve_period_id(iso_date, period_id)
    with _session() as db:
        if tutoring_only:
            db.query(ClassScheduleRow).filter(
                ClassScheduleRow.slot_date == target,
                ClassScheduleRow.is_fixed.is_(False),
            ).delete(synchronize_session=False)
        else:
            db.query(ClassScheduleRow).filter(ClassScheduleRow.slot_date == target).delete(
                synchronize_session=False
            )
        for item in rows:
            is_fixed = item.get("is_fixed")
            if is_fixed is None:
                is_fixed = (item.get("lesson_kind") or "講習") == "通常"
            db.add(
                ClassScheduleRow(
                    period_id=pid,
                    slot_date=target,
                    student_id=int(item["student_id"]),
                    student_name=item["student_name"],
                    subject=item.get("subject") or "",
                    teacher_id=int(item["teacher_id"]),
                    teacher_name=item["teacher_name"],
                    slot=int(item["slot"]),
                    is_fixed=bool(is_fixed),
                    source=item.get("source") or "manual",
                )
            )
        db.commit()


def save_assignments_for_date(iso_date: str, assignments: list[dict]) -> None:
    """互換: 講習のみ差し替え＋通常行をマージ（Excel 取込用）。"""
    pid = _resolve_period_id(iso_date)
    fixed_rows = get_schedules_for_date(iso_date, fixed_only=True)

    def _is_tutoring(row: dict) -> bool:
        if row.get("is_fixed"):
            return False
        return (row.get("lesson_kind") or "講習") != "通常"

    tutoring = [a for a in assignments if _is_tutoring(a)]
    merged = fixed_rows + tutoring
    save_schedules_for_date(iso_date, merged, period_id=pid, tutoring_only=False)


def get_fixed_slots_for_entity(
    period_id: int,
    role: str,
    entity_id: int,
    iso_date: str,
) -> set[str]:
    """is_fixed=True の枠（スロットキー集合）。講習期間中は年度 REGULAR も参照する。"""
    target = date.fromisoformat(iso_date)
    id_col = ClassScheduleRow.student_id if role == "student" else ClassScheduleRow.teacher_id
    period_ids = [period_id]
    period = get_period(period_id)
    if getattr(period, "period_kind", "CRAM") == "CRAM":
        from services.fiscal_year_store import find_regular_period_for_date

        regular = find_regular_period_for_date(iso_date)
        if regular is not None and regular.id not in period_ids:
            period_ids.append(regular.id)
    slots: set[str] = set()
    with _session() as db:
        for pid in period_ids:
            rows = db.scalars(
                select(ClassScheduleRow).where(
                    ClassScheduleRow.period_id == pid,
                    ClassScheduleRow.slot_date == target,
                    ClassScheduleRow.is_fixed.is_(True),
                    id_col == entity_id,
                )
            ).all()
            for row in rows:
                key = str(row.slot)
                if key in SLOT_KEYS:
                    slots.add(key)
    return slots


def get_fixed_slot_keys_for_entity(
    period_id: int,
    role: str,
    entity_id: int,
    iso_date: str,
) -> dict[str, str]:
    """互換: 固定枠を ◎ ではなく空文字＋ locked_slots で扱うため、空 dict を返す。"""
    del period_id, role, entity_id, iso_date
    return {}


def build_period_schedule(period_id: int, *, fixed_only: bool | None = None) -> dict:
    period = get_period(period_id)
    open_dates = open_dates_for_period(period)
    time_slots = generate_time_slots()
    all_rows = get_schedules_between(period.start_date, period.end_date, fixed_only=fixed_only)
    by_date: dict[str, list[dict]] = {d: [] for d in open_dates}
    for row in all_rows:
        if row["date"] in by_date:
            by_date[row["date"]].append(row)
    return {
        "period_id": period_id,
        "period_name": period.name,
        "filter": "fixed_only" if fixed_only else ("tutoring_only" if fixed_only is False else "full"),
        "dates": open_dates,
        "time_slots": time_slots,
        "schedules_by_date": by_date,
        "schedules": all_rows,
        "total": len(all_rows),
    }


def get_full_schedule(period_id: int) -> dict:
    return build_period_schedule(period_id, fixed_only=None)


def get_fixed_only_schedule(period_id: int) -> dict:
    return build_period_schedule(period_id, fixed_only=True)


def get_tutoring_only_schedule(period_id: int) -> dict:
    return build_period_schedule(period_id, fixed_only=False)


def reset_class_schedules_for_tests() -> None:
    with _session() as db:
        db.query(ClassScheduleRow).delete()
        db.commit()


def migrate_from_assignments_table() -> int:
    """assignments → class_schedules へ一度だけコピー。"""
    from models import Assignment as AssignmentRow

    with _session() as db:
        if db.scalar(select(ClassScheduleRow.id).limit(1)) is not None:
            return 0
        legacy = db.scalars(select(AssignmentRow).order_by(AssignmentRow.id)).all()
        count = 0
        for row in legacy:
            period = find_period_for_date(row.slot_date.isoformat())
            if period is None:
                continue
            is_fixed = (getattr(row, "lesson_kind", None) or "講習") == "通常"
            db.add(
                ClassScheduleRow(
                    period_id=period.id,
                    slot_date=row.slot_date,
                    slot=row.slot,
                    teacher_id=row.teacher_id,
                    teacher_name=row.teacher_name,
                    student_id=row.student_id,
                    student_name=row.student_name,
                    subject=row.subject,
                    is_fixed=is_fixed,
                    source="legacy",
                )
            )
            count += 1
        db.commit()
        return count
