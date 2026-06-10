import json
from copy import deepcopy

from fastapi import HTTPException

from config import DATA_DIR
from schemas.assignment import AssignmentRecord

ASSIGNMENTS_PATH = DATA_DIR / "assignments.json"
REQUESTS_PATH = DATA_DIR / "assignment-requests.json"


def _read_object(path) -> dict:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=f"{path.name} must be a JSON object")
    return data


def _write_object(path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_assignments_for_date(date: str) -> list[dict]:
    store = _read_object(ASSIGNMENTS_PATH)
    return deepcopy(store.get(date, []))


def get_assignment_requests_for_date(date: str) -> list[dict]:
    store = _read_object(REQUESTS_PATH)
    return deepcopy(store.get(date, []))


def save_assignments_for_date(date: str, assignments: list[dict]) -> None:
    store = _read_object(ASSIGNMENTS_PATH)
    store[date] = assignments
    _write_object(ASSIGNMENTS_PATH, store)


def add_assignment(record: AssignmentRecord) -> None:
    store = _read_object(ASSIGNMENTS_PATH)
    rows = store.setdefault(record.date, [])
    rows.append(record.model_dump())
    _write_object(ASSIGNMENTS_PATH, store)


def clear_requests_fulfilled(date: str, fulfilled_student_ids: set[int]) -> None:
    store = _read_object(REQUESTS_PATH)
    pending = store.get(date, [])
    store[date] = [r for r in pending if r["student_id"] not in fulfilled_student_ids]
    _write_object(REQUESTS_PATH, store)
