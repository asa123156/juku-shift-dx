"""講師コマごとの 1対2 / 1対4（max_lanes）設定。"""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal
from models import TeacherSlotCapacity
from services.teacher_slot_lanes import build_teacher_lanes

DEFAULT_MAX_LANES = 2
ALLOWED_MAX_LANES = frozenset({2, 4})


def _session() -> Session:
    return SessionLocal()


def lesson_format_label(max_lanes: int) -> str:
    return "1対4" if max_lanes >= 4 else "1対2"


def normalize_max_lanes(value: int) -> int:
    if value not in ALLOWED_MAX_LANES:
        raise HTTPException(status_code=400, detail="max_lanes は 2（1対2）または 4（1対4）のみ指定できます")
    return value


def get_capacity_map_for_date(iso_date: str) -> dict[tuple[int, int], int]:
    slot_date = date.fromisoformat(iso_date)
    with _session() as db:
        rows = db.scalars(
            select(TeacherSlotCapacity).where(TeacherSlotCapacity.slot_date == slot_date)
        ).all()
    return {(row.teacher_id, row.slot): row.max_lanes for row in rows}


def get_max_lanes(teacher_id: int, iso_date: str, slot: int) -> int:
    slot_date = date.fromisoformat(iso_date)
    with _session() as db:
        row = db.scalars(
            select(TeacherSlotCapacity).where(
                TeacherSlotCapacity.teacher_id == teacher_id,
                TeacherSlotCapacity.slot_date == slot_date,
                TeacherSlotCapacity.slot == slot,
            )
        ).first()
    return row.max_lanes if row is not None else DEFAULT_MAX_LANES


def _placed_assignment_count(avail: str, assignments: list[dict], max_lanes: int) -> int:
    lanes = build_teacher_lanes(avail, assignments, max_lanes=max_lanes)
    return sum(1 for lane in lanes if lane.get("assignment"))


def set_max_lanes(
    teacher_id: int,
    iso_date: str,
    slot: int,
    max_lanes: int,
    *,
    avail: str = "",
    assignments: list[dict] | None = None,
) -> int:
    max_lanes = normalize_max_lanes(max_lanes)
    slot_date = date.fromisoformat(iso_date)
    at_slot = assignments or []
    placed = _placed_assignment_count(avail, at_slot, max_lanes)
    if placed < len(at_slot):
        raise HTTPException(
            status_code=409,
            detail=f"現在 {len(at_slot)} 件の割当があり、{lesson_format_label(max_lanes)} には収まりません。先に割当を減らしてください",
        )

    with _session() as db:
        row = db.scalars(
            select(TeacherSlotCapacity).where(
                TeacherSlotCapacity.teacher_id == teacher_id,
                TeacherSlotCapacity.slot_date == slot_date,
                TeacherSlotCapacity.slot == slot,
            )
        ).first()
        if max_lanes == DEFAULT_MAX_LANES and not at_slot:
            if row is not None:
                db.delete(row)
                db.commit()
            return DEFAULT_MAX_LANES
        if row is None:
            row = TeacherSlotCapacity(
                teacher_id=teacher_id,
                slot_date=slot_date,
                slot=slot,
                max_lanes=max_lanes,
            )
            db.add(row)
        else:
            row.max_lanes = max_lanes
        db.commit()
    return max_lanes
