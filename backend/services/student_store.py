import json

from fastapi import HTTPException

from config import DATA_DIR
from schemas.period import SlotSymbol, empty_slots

SUBMISSIONS_PATH = DATA_DIR / "student-submissions.json"

LEGACY_TO_SYMBOL: dict[str, SlotSymbol] = {
    "regular_class": "◎",
    "unavailable": "×",
    "available": "",
    "blank": "",
    "priority": "◎",
}


def _read_store() -> dict:
    if not SUBMISSIONS_PATH.is_file():
        return {}
    with SUBMISSIONS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="student-submissions.json must be an object")
    return data


def _write_store(data: dict) -> None:
    SUBMISSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SUBMISSIONS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _normalize_slots(raw: dict[str, str]) -> dict[str, SlotSymbol]:
    out: dict[str, SlotSymbol] = empty_slots()
    for key in ("1", "2", "3", "4"):
        val = raw.get(key, "")
        if val in ("◎", "×", ""):
            out[key] = val  # type: ignore[assignment]
        elif val in LEGACY_TO_SYMBOL:
            out[key] = LEGACY_TO_SYMBOL[val]
    return out


def get_student_submission(student_id: int, iso_date: str) -> dict[str, SlotSymbol] | None:
    store = _read_store()
    raw = store.get(iso_date, {}).get(str(student_id))
    if raw is None:
        return None
    return _normalize_slots(raw)


def save_student_day(student_id: int, iso_date: str, slots: dict[str, SlotSymbol]) -> None:
    store = _read_store()
    store.setdefault(iso_date, {})[str(student_id)] = dict(slots)
    _write_store(store)


def save_student_bulk(student_id: int, submissions: list[dict]) -> list[str]:
    saved: list[str] = []
    for row in submissions:
        iso_date = row["date"]
        save_student_day(student_id, iso_date, row["slots"])
        saved.append(iso_date)
    return saved
