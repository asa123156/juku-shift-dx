import json
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import DATA_DIR
from database import SessionLocal
from models import AppSetting, PeriodBaseSlot, Period as PeriodRow
from schemas.period import Period, PeriodStatus, empty_slots

PERIODS_PATH = DATA_DIR / "periods.json"
BASES_PATH = DATA_DIR / "period-bases.json"

ACTIVE_PERIOD_KEY = "active_period_id"


def _session() -> Session:
    return SessionLocal()


def _read_json(path) -> dict:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=f"{path.name} must be a JSON object")
    return data


def _to_schema(row: PeriodRow) -> Period:
    return Period(
        id=row.id,
        name=row.name,
        start_date=row.start_date.isoformat(),
        end_date=row.end_date.isoformat(),
        status=row.status,
    )


def _get_active_period_id(db: Session) -> int | None:
    row = db.get(AppSetting, ACTIVE_PERIOD_KEY)
    if row is None:
        return None
    try:
        return int(row.value)
    except ValueError:
        return None


def _set_active_period_id(db: Session, period_id: int) -> None:
    row = db.get(AppSetting, ACTIVE_PERIOD_KEY)
    if row is None:
        db.add(AppSetting(key=ACTIVE_PERIOD_KEY, value=str(period_id)))
    else:
        row.value = str(period_id)


def iter_dates(start: str, end: str) -> list[str]:
    current = date.fromisoformat(start)
    last = date.fromisoformat(end)
    out: list[str] = []
    while current <= last:
        out.append(current.isoformat())
        current += timedelta(days=1)
    return out


def list_periods() -> tuple[list[Period], int | None]:
    with _session() as db:
        rows = db.scalars(select(PeriodRow).order_by(PeriodRow.id)).all()
        return [_to_schema(row) for row in rows], _get_active_period_id(db)


def get_period(period_id: int) -> Period:
    with _session() as db:
        row = db.get(PeriodRow, period_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Period id={period_id} not found")
        return _to_schema(row)


def find_period_for_date(iso_date: str) -> Period | None:
    target = date.fromisoformat(iso_date)
    with _session() as db:
        rows = db.scalars(select(PeriodRow)).all()
        for row in rows:
            if row.start_date <= target <= row.end_date:
                return _to_schema(row)
    return None


def create_period(name: str, start_date: str, end_date: str) -> Period:
    with _session() as db:
        row = PeriodRow(
            name=name,
            start_date=date.fromisoformat(start_date),
            end_date=date.fromisoformat(end_date),
            status="DRAFT",
        )
        db.add(row)
        db.flush()
        _set_active_period_id(db, row.id)
        db.commit()
        db.refresh(row)
        period = _to_schema(row)
    return period


def update_period_status(period_id: int, status: PeriodStatus) -> Period:
    with _session() as db:
        row = db.get(PeriodRow, period_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Period id={period_id} not found")
        row.status = status
        db.commit()
        db.refresh(row)
        return _to_schema(row)


def seed_periods_if_empty() -> None:
    """DB が空のとき periods.json から初期データを投入する。"""
    with _session() as db:
        if db.scalar(select(PeriodRow.id).limit(1)) is not None:
            return
        store = _read_json(PERIODS_PATH)
        items = store.get("items", [])
        if not items:
            return
        json_id_to_db_id: dict[int, int] = {}
        for raw in items:
            row = PeriodRow(
                name=raw["name"],
                start_date=date.fromisoformat(raw["start_date"]),
                end_date=date.fromisoformat(raw["end_date"]),
                status=raw["status"],
            )
            db.add(row)
            db.flush()
            json_id_to_db_id[int(raw["id"])] = row.id
        active_id = store.get("active_period_id")
        if active_id is not None:
            mapped = json_id_to_db_id.get(int(active_id))
            if mapped is not None:
                _set_active_period_id(db, mapped)
        db.commit()


def _import_bases_from_json(db: Session, raw: dict) -> None:
    role_map = {"teachers": "teacher", "students": "student"}
    for json_key, period_data in raw.items():
        if not json_key.isdigit():
            continue
        period_id = int(json_key)
        if db.get(PeriodRow, period_id) is None:
            continue
        for role_key, entities in period_data.items():
            role = role_map.get(role_key)
            if role is None or not isinstance(entities, dict):
                continue
            for entity_key, days in entities.items():
                if not entity_key.isdigit() or not isinstance(days, dict):
                    continue
                entity_id = int(entity_key)
                for iso_date, slots in days.items():
                    if not isinstance(slots, dict):
                        continue
                    slot_date = date.fromisoformat(iso_date)
                    for slot_key, symbol in slots.items():
                        if slot_key not in ("1", "2", "3", "4") or not symbol:
                            continue
                        db.add(
                            PeriodBaseSlot(
                                period_id=period_id,
                                role=role,
                                entity_id=entity_id,
                                slot_date=slot_date,
                                slot_key=slot_key,
                                symbol=symbol,
                            )
                        )


def seed_period_bases_if_empty() -> None:
    """DB が空のとき period-bases.json から ◎ 固定枠を投入する。"""
    with _session() as db:
        if db.scalar(select(PeriodBaseSlot.id).limit(1)) is not None:
            return
        raw = _read_json(BASES_PATH)
        if not raw:
            return
        _import_bases_from_json(db, raw)
        db.commit()


def reset_periods_for_tests() -> None:
    """テスト用: periods / app_settings をクリアし JSON から再投入。"""
    from database import Base, engine

    import models  # noqa: F401 — register ORM models

    Base.metadata.create_all(bind=engine)
    with _session() as db:
        db.query(PeriodBaseSlot).delete()
        db.query(PeriodRow).delete()
        db.query(AppSetting).delete()
        db.commit()
    seed_periods_if_empty()
    seed_period_bases_if_empty()


def set_period_base_slot(
    period_id: int,
    role: str,
    entity_id: int,
    iso_date: str,
    slot: str,
    symbol: str,
) -> None:
    with _session() as db:
        if db.get(PeriodRow, period_id) is None:
            raise HTTPException(status_code=404, detail=f"Period id={period_id} not found")
        target_date = date.fromisoformat(iso_date)
        existing = db.scalars(
            select(PeriodBaseSlot).where(
                PeriodBaseSlot.period_id == period_id,
                PeriodBaseSlot.role == role,
                PeriodBaseSlot.entity_id == entity_id,
                PeriodBaseSlot.slot_date == target_date,
                PeriodBaseSlot.slot_key == slot,
            )
        ).first()
        if existing is not None:
            existing.symbol = symbol
        else:
            db.add(
                PeriodBaseSlot(
                    period_id=period_id,
                    role=role,
                    entity_id=entity_id,
                    slot_date=target_date,
                    slot_key=slot,
                    symbol=symbol,
                )
            )
        db.commit()


def get_entity_base_day(period_id: int, role: str, entity_id: int, iso_date: str) -> dict[str, str]:
    target_date = date.fromisoformat(iso_date)
    with _session() as db:
        rows = db.scalars(
            select(PeriodBaseSlot).where(
                PeriodBaseSlot.period_id == period_id,
                PeriodBaseSlot.role == role,
                PeriodBaseSlot.entity_id == entity_id,
                PeriodBaseSlot.slot_date == target_date,
            )
        ).all()
    result = empty_slots()
    for row in rows:
        if row.slot_key in result:
            result[row.slot_key] = row.symbol
    return result
