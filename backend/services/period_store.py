import json
from datetime import date, timedelta

from fastapi import HTTPException

from config import DATA_DIR
from schemas.period import Period, PeriodStatus, empty_slots

PERIODS_PATH = DATA_DIR / "periods.json"
BASES_PATH = DATA_DIR / "period-bases.json"


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


def iter_dates(start: str, end: str) -> list[str]:
    current = date.fromisoformat(start)
    last = date.fromisoformat(end)
    out: list[str] = []
    while current <= last:
        out.append(current.isoformat())
        current += timedelta(days=1)
    return out


def list_periods() -> tuple[list[Period], int | None]:
    store = _read_json(PERIODS_PATH)
    items = [Period.model_validate(p) for p in store.get("items", [])]
    return items, store.get("active_period_id")


def get_period(period_id: int) -> Period:
    for period in list_periods()[0]:
        if period.id == period_id:
            return period
    raise HTTPException(status_code=404, detail=f"Period id={period_id} not found")


def find_period_for_date(iso_date: str) -> Period | None:
    for period in list_periods()[0]:
        if period.start_date <= iso_date <= period.end_date:
            return period
    return None


def create_period(name: str, start_date: str, end_date: str) -> Period:
    store = _read_json(PERIODS_PATH)
    next_id = int(store.get("next_id", 1))
    period = Period(id=next_id, name=name, start_date=start_date, end_date=end_date, status="DRAFT")
    store.setdefault("items", []).append(period.model_dump())
    store["next_id"] = next_id + 1
    store["active_period_id"] = next_id
    _write_json(PERIODS_PATH, store)
    _init_period_bases(next_id, start_date, end_date)
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
    store = _read_json(PERIODS_PATH)
    updated: Period | None = None
    for raw in store.get("items", []):
        if raw["id"] == period_id:
            raw["status"] = status
            updated = Period.model_validate(raw)
            break
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Period id={period_id} not found")
    _write_json(PERIODS_PATH, store)
    return updated


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
