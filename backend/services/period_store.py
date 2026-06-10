import json
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import DATA_DIR
from database import SessionLocal
from models import AppSetting, Period as PeriodRow
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


def _write_json(path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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
    _init_period_bases(period.id, start_date, end_date)
    return period


def _init_period_bases(period_id: int, start_date: str, end_date: str) -> None:
    bases = _read_json(BASES_PATH)
    dates = iter_dates(start_date, end_date)
    bases[str(period_id)] = {
        "teachers": {},
        "students": {},
        "_dates_initialized": dates,
    }
    _write_json(BASES_PATH, bases)


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


def reset_periods_for_tests() -> None:
    """テスト用: periods / app_settings をクリアし JSON から再投入。"""
    from database import Base, engine

    import models  # noqa: F401 — register ORM models

    Base.metadata.create_all(bind=engine)
    with _session() as db:
        db.query(PeriodRow).delete()
        db.query(AppSetting).delete()
        db.commit()
    seed_periods_if_empty()


def get_period_base(period_id: int) -> dict:
    bases = _read_json(BASES_PATH)
    return bases.get(str(period_id), {"teachers": {}, "students": {}})


def set_period_base_slot(
    period_id: int,
    role: str,
    entity_id: int,
    iso_date: str,
    slot: str,
    symbol: str,
) -> None:
    bases = _read_json(BASES_PATH)
    period_key = str(period_id)
    if period_key not in bases:
        raise HTTPException(status_code=404, detail=f"Period base id={period_id} not found")
    role_key = "teachers" if role == "teacher" else "students"
    entity_key = str(entity_id)
    period_data = bases[period_key]
    period_data.setdefault(role_key, {})
    period_data[role_key].setdefault(entity_key, {})
    period_data[role_key][entity_key].setdefault(iso_date, empty_slots())
    period_data[role_key][entity_key][iso_date][slot] = symbol
    _write_json(BASES_PATH, bases)


def get_entity_base_day(period_id: int, role: str, entity_id: int, iso_date: str) -> dict[str, str]:
    base = get_period_base(period_id)
    role_key = "teachers" if role == "teacher" else "students"
    entity = base.get(role_key, {}).get(str(entity_id), {})
    day = entity.get(iso_date)
    if day:
        return {**empty_slots(), **day}
    return empty_slots()
