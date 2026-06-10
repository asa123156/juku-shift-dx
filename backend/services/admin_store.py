import json
from copy import deepcopy
from datetime import date
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import DATA_DIR
from database import SessionLocal
from models import AdminOverride
from schemas.shifts import ShiftStatus

OVERRIDES_PATH = DATA_DIR / "admin-overrides.json"
_SLOT_FIELDS = ("s1", "s2", "s3", "s4")


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


def _import_overrides_from_json(db: Session, raw: dict) -> None:
    for iso_date, teachers in raw.items():
        if not isinstance(teachers, dict):
            continue
        slot_date = date.fromisoformat(iso_date)
        for teacher_key, slots in teachers.items():
            if not teacher_key.isdigit() or not isinstance(slots, dict):
                continue
            teacher_id = int(teacher_key)
            for slot_key, status in slots.items():
                if slot_key not in ("1", "2", "3", "4") or not status:
                    continue
                db.add(
                    AdminOverride(
                        teacher_id=teacher_id,
                        slot_date=slot_date,
                        slot_key=slot_key,
                        status=status,
                    )
                )


def seed_admin_overrides_if_empty() -> None:
    """DB が空のとき admin-overrides.json から教室長上書きを投入する。"""
    with _session() as db:
        if db.scalar(select(AdminOverride.id).limit(1)) is not None:
            return
        raw = _read_json(OVERRIDES_PATH)
        if not raw:
            return
        _import_overrides_from_json(db, raw)
        db.commit()


def reset_admin_overrides_for_tests() -> None:
    """テスト用: 教室長上書きをすべて削除する。"""
    from database import Base, engine

    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with _session() as db:
        db.query(AdminOverride).delete()
        db.commit()


def _upsert_override(
    db: Session,
    teacher_id: int,
    slot_date: date,
    slot_key: str,
    status: ShiftStatus,
) -> None:
    existing = db.scalars(
        select(AdminOverride).where(
            AdminOverride.teacher_id == teacher_id,
            AdminOverride.slot_date == slot_date,
            AdminOverride.slot_key == slot_key,
        )
    ).first()
    if existing is not None:
        existing.status = status
    else:
        db.add(
            AdminOverride(
                teacher_id=teacher_id,
                slot_date=slot_date,
                slot_key=slot_key,
                status=status,
            )
        )


def get_overrides_for_date(iso_date: str) -> dict[str, dict[str, str]]:
    target_date = date.fromisoformat(iso_date)
    with _session() as db:
        rows = db.scalars(
            select(AdminOverride).where(AdminOverride.slot_date == target_date)
        ).all()
    by_teacher: dict[str, dict[str, str]] = {}
    for row in rows:
        by_teacher.setdefault(str(row.teacher_id), {})[row.slot_key] = row.status
    return by_teacher


def set_slot_status(
    iso_date: str,
    teacher_id: int,
    slot: int,
    status: ShiftStatus,
) -> None:
    target_date = date.fromisoformat(iso_date)
    with _session() as db:
        _upsert_override(db, teacher_id, target_date, str(slot), status)
        db.commit()


def confirm_all_pending(iso_date: str, dashboard: dict) -> int:
    """待機のコマをすべて確定にする。変更したコマ数を返す。"""
    target_date = date.fromisoformat(iso_date)
    changed = 0
    with _session() as db:
        for teacher in dashboard.get("teachers", []):
            teacher_id = teacher["id"]
            for slot_num, field in enumerate(_SLOT_FIELDS, start=1):
                if teacher.get(field) == "待機":
                    _upsert_override(db, teacher_id, target_date, str(slot_num), "確定")
                    changed += 1
        db.commit()
    return changed


def apply_admin_overrides(dashboard: dict) -> dict:
    result = deepcopy(dashboard)
    iso_date = result.get("date")
    if not iso_date:
        return result

    overrides = get_overrides_for_date(iso_date)
    for teacher in result.get("teachers", []):
        teacher_overrides = overrides.get(str(teacher["id"]))
        if not teacher_overrides:
            continue
        for slot_num, field in enumerate(_SLOT_FIELDS, start=1):
            key = str(slot_num)
            if key in teacher_overrides:
                teacher[field] = teacher_overrides[key]

    return result
