from services.slot_timing import SLOT_KEYS
from services.submission_store import get_entity_day, upsert_entity_day


def get_student_submission(student_id: int, iso_date: str) -> dict[str, str] | None:
    return get_entity_day("student", student_id, iso_date)


def save_student_day(student_id: int, iso_date: str, slots: dict[str, str]) -> None:
    upsert_entity_day("student", student_id, iso_date, slots)


def save_student_bulk(student_id: int, submissions: list[dict]) -> list[str]:
    saved: list[str] = []
    for row in submissions:
        iso_date = row["date"]
        save_student_day(student_id, iso_date, row["slots"])
        saved.append(iso_date)
    return saved
