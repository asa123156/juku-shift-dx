from schemas.period import SlotSymbol, empty_slots
from services.submission_store import get_entity_day, upsert_entity_day

LEGACY_TO_SYMBOL: dict[str, SlotSymbol] = {
    "regular_class": "◎",
    "unavailable": "×",
    "available": "",
    "blank": "",
    "priority": "◎",
}


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
    return get_entity_day("student", student_id, iso_date)


def save_student_day(student_id: int, iso_date: str, slots: dict[str, SlotSymbol]) -> None:
    upsert_entity_day("student", student_id, iso_date, slots)


def save_student_bulk(student_id: int, submissions: list[dict]) -> list[str]:
    saved: list[str] = []
    for row in submissions:
        iso_date = row["date"]
        save_student_day(student_id, iso_date, row["slots"])
        saved.append(iso_date)
    return saved
