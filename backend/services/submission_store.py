import json
from datetime import date
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import DATA_DIR
from database import SessionLocal
from models import ShiftSubmission
from schemas.period import SlotSymbol, empty_slots

TEACHER_SUBMISSIONS_PATH = DATA_DIR / "teacher-submissions.json"
STUDENT_SUBMISSIONS_PATH = DATA_DIR / "student-submissions.json"


def _session() -> Session:
    return SessionLocal()


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=f"{path.name} must be a JSON object")
    return data


def _import_submissions_from_json(db: Session, raw: dict, role: str) -> None:
    for iso_date, entities in raw.items():
        if not isinstance(entities, dict):
            continue
        slot_date = date.fromisoformat(iso_date)
        for entity_key, slots in entities.items():
            if not entity_key.isdigit() or not isinstance(slots, dict):
                continue
            entity_id = int(entity_key)
            for slot_key, symbol in slots.items():
                if slot_key not in ("1", "2", "3", "4"):
                    continue
                db.add(
                    ShiftSubmission(
                        role=role,
                        entity_id=entity_id,
                        slot_date=slot_date,
                        slot_key=slot_key,
                        symbol=symbol,
                    )
                )


def seed_shift_submissions_if_empty() -> None:
    """DB が空のとき teacher/student JSON から提出データを投入する。"""
    with _session() as db:
        if db.scalar(select(ShiftSubmission.id).limit(1)) is not None:
            return
        _import_submissions_from_json(db, _read_json(TEACHER_SUBMISSIONS_PATH), "teacher")
        _import_submissions_from_json(db, _read_json(STUDENT_SUBMISSIONS_PATH), "student")
        db.commit()


def reset_submissions_for_tests() -> None:
    """テスト用: 提出データをすべて削除する。"""
    from database import Base, engine

    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with _session() as db:
        db.query(ShiftSubmission).delete()
        db.commit()


def get_entity_day(role: str, entity_id: int, iso_date: str) -> dict[str, SlotSymbol] | None:
    target_date = date.fromisoformat(iso_date)
    with _session() as db:
        rows = db.scalars(
            select(ShiftSubmission).where(
                ShiftSubmission.role == role,
                ShiftSubmission.entity_id == entity_id,
                ShiftSubmission.slot_date == target_date,
            )
        ).all()
    if not rows:
        return None
    result = empty_slots()
    for row in rows:
        if row.slot_key in result:
            result[row.slot_key] = row.symbol  # type: ignore[assignment]
    return result


def upsert_entity_day(role: str, entity_id: int, iso_date: str, slots: dict[str, SlotSymbol]) -> None:
    target_date = date.fromisoformat(iso_date)
    with _session() as db:
        for slot_key in ("1", "2", "3", "4"):
            symbol = slots.get(slot_key, "")
            existing = db.scalars(
                select(ShiftSubmission).where(
                    ShiftSubmission.role == role,
                    ShiftSubmission.entity_id == entity_id,
                    ShiftSubmission.slot_date == target_date,
                    ShiftSubmission.slot_key == slot_key,
                )
            ).first()
            if existing is not None:
                existing.symbol = symbol
            else:
                db.add(
                    ShiftSubmission(
                        role=role,
                        entity_id=entity_id,
                        slot_date=target_date,
                        slot_key=slot_key,
                        symbol=symbol,
                    )
                )
        db.commit()


def get_submissions_for_date(role: str, iso_date: str) -> dict[int, dict[str, SlotSymbol]]:
    target_date = date.fromisoformat(iso_date)
    with _session() as db:
        rows = db.scalars(
            select(ShiftSubmission).where(
                ShiftSubmission.role == role,
                ShiftSubmission.slot_date == target_date,
            )
        ).all()
    grouped: dict[int, dict[str, SlotSymbol]] = {}
    for row in rows:
        grouped.setdefault(row.entity_id, empty_slots())
        if row.slot_key in grouped[row.entity_id]:
            grouped[row.entity_id][row.slot_key] = row.symbol  # type: ignore[assignment]
    return grouped
