import json
from copy import deepcopy

from fastapi import HTTPException

from config import DATA_DIR
from schemas.shifts import AvailabilityStatus, ShiftStatus

SUBMISSIONS_PATH = DATA_DIR / "teacher-submissions.json"

_AVAILABILITY_TO_DASHBOARD: dict[AvailabilityStatus, ShiftStatus] = {
    "regular_class": "通常授業",
    "available": "待機",
    "unavailable": "不可",
    "blank": "未提出",
}

_SLOT_FIELDS = ("s1", "s2", "s3", "s4")


def availability_to_dashboard(status: AvailabilityStatus) -> ShiftStatus:
    return _AVAILABILITY_TO_DASHBOARD[status]


def dashboard_to_availability(status: ShiftStatus) -> AvailabilityStatus:
    if status == "通常授業":
        return "regular_class"
    if status in ("待機", "確定", "AI提案"):
        return "available"
    if status == "不可":
        return "unavailable"
    return "blank"


def compute_metrics(teachers: list[dict]) -> dict[str, int]:
    unsubmitted = 0
    shortage = 0
    for teacher in teachers:
        statuses = [teacher.get(f) for f in _SLOT_FIELDS]
        if any(s == "未提出" for s in statuses):
            unsubmitted += 1
        shortage += sum(1 for s in statuses if s == "不足")
    return {
        "unsubmitted_teachers": unsubmitted,
        "shortage_slots": shortage,
    }


def _load_submissions_file() -> dict[str, dict[str, dict[str, str]]]:
    if not SUBMISSIONS_PATH.is_file():
        return {}
    with SUBMISSIONS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="teacher-submissions.json must be an object")
    return data


def _save_submissions_file(data: dict[str, dict[str, dict[str, str]]]) -> None:
    SUBMISSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SUBMISSIONS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_teacher_submission(teacher_id: int, date: str) -> dict[str, AvailabilityStatus] | None:
    store = _load_submissions_file()
    by_date = store.get(date)
    if not by_date:
        return None
    raw = by_date.get(str(teacher_id))
    if raw is None:
        return None
    normalized: dict[str, AvailabilityStatus] = {}
    for k, v in raw.items():
        if v == "priority":  # 旧値との互換
            normalized[k] = "regular_class"
        else:
            normalized[k] = v  # type: ignore[assignment]
    return normalized


def save_teacher_submission(
    teacher_id: int,
    date: str,
    slots: dict[str, AvailabilityStatus],
) -> dict[str, ShiftStatus]:
    store = _load_submissions_file()
    existing = store.get(date, {}).get(str(teacher_id), {})
    merged: dict[str, str] = {**existing, **slots}
    store.setdefault(date, {})[str(teacher_id)] = merged
    _save_submissions_file(store)
    return {
        f"s{i}": availability_to_dashboard(merged.get(str(i), "blank"))  # type: ignore[arg-type]
        for i in range(1, 5)
    }


def update_single_slot(
    teacher_id: int,
    date: str,
    slot: int,
    status: AvailabilityStatus,
) -> dict[str, ShiftStatus]:
    current = get_teacher_submission(teacher_id, date) or {}
    current[str(slot)] = status
    return save_teacher_submission(teacher_id, date, current)


def apply_teacher_submissions(dashboard: dict) -> dict:
    result = deepcopy(dashboard)
    date = result.get("date")
    if not date:
        return result

    store = _load_submissions_file()
    by_date = store.get(date, {})

    for teacher in result.get("teachers", []):
        submitted = by_date.get(str(teacher["id"]))
        if not submitted:
            continue
        for slot_num, field in enumerate(_SLOT_FIELDS, start=1):
            key = str(slot_num)
            if key in submitted:
                teacher[field] = availability_to_dashboard(submitted[key])  # type: ignore[arg-type]

    return result


def build_teacher_submission_response(
    teacher_id: int,
    date: str,
    dashboard: dict,
) -> dict:
    saved = get_teacher_submission(teacher_id, date)
    if saved is not None:
        return {"teacher_id": teacher_id, "date": date, "slots": saved}

    teacher = next((t for t in dashboard.get("teachers", []) if t["id"] == teacher_id), None)
    if teacher is None:
        raise HTTPException(
            status_code=404,
            detail=f"Teacher id={teacher_id} not found for date={date}",
        )
    slots = {str(i): dashboard_to_availability(teacher[f"s{i}"]) for i in range(1, 5)}
    return {"teacher_id": teacher_id, "date": date, "slots": slots}


def ensure_teacher_exists(dashboard: dict, teacher_id: int) -> None:
    teacher_ids = {t["id"] for t in dashboard.get("teachers", [])}
    if teacher_id not in teacher_ids:
        raise HTTPException(status_code=404, detail=f"Teacher id={teacher_id} not found")
