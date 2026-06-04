import json
from copy import deepcopy
from pathlib import Path

from fastapi import HTTPException

from schemas.shifts import AvailabilityStatus, ShiftStatus

BACKEND_DIR = Path(__file__).resolve().parent.parent
SUBMISSIONS_PATH = BACKEND_DIR / "data" / "teacher-submissions.json"

# 講師入力（英語）→ 教室長ダッシュボード（日本語）
_AVAILABILITY_TO_DASHBOARD: dict[AvailabilityStatus, ShiftStatus] = {
    "available": "待機",
    "unavailable": "不可",
    "blank": "未提出",
}

_SLOT_FIELDS = ("s1", "s2", "s3", "s4")


def availability_to_dashboard(status: AvailabilityStatus) -> ShiftStatus:
    return _AVAILABILITY_TO_DASHBOARD[status]


def dashboard_to_availability(status: ShiftStatus) -> AvailabilityStatus:
    if status in ("待機", "確定"):
        return "available"
    if status == "不可":
        return "unavailable"
    return "blank"


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


def _date_key(date: str) -> str:
    return date


def _teacher_key(teacher_id: int) -> str:
    return str(teacher_id)


def get_teacher_submission(teacher_id: int, date: str) -> dict[str, AvailabilityStatus] | None:
    store = _load_submissions_file()
    by_date = store.get(_date_key(date))
    if not by_date:
        return None
    raw = by_date.get(_teacher_key(teacher_id))
    if raw is None:
        return None
    return {k: v for k, v in raw.items()}  # type: ignore[misc]


def save_teacher_submission(
    teacher_id: int,
    date: str,
    slots: dict[str, AvailabilityStatus],
) -> dict[str, ShiftStatus]:
    store = _load_submissions_file()
    existing = store.get(_date_key(date), {}).get(_teacher_key(teacher_id), {})
    merged: dict[str, str] = {**existing, **slots}
    store.setdefault(_date_key(date), {})[_teacher_key(teacher_id)] = merged
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


def apply_submissions_to_dashboard(dashboard: dict) -> dict:
    """提出済みデータで該当講師行を上書きし、metrics を再計算する"""
    result = deepcopy(dashboard)
    date = result.get("date")
    if not date:
        return result

    store = _load_submissions_file()
    by_date = store.get(_date_key(date), {})

    for teacher in result.get("teachers", []):
        tid = _teacher_key(teacher["id"])
        submitted = by_date.get(tid)
        if not submitted:
            continue
        for slot_num, field in enumerate(_SLOT_FIELDS, start=1):
            key = str(slot_num)
            if key in submitted:
                teacher[field] = availability_to_dashboard(submitted[key])  # type: ignore[arg-type]

    result["metrics"] = _compute_metrics(result.get("teachers", []))
    return result


def _compute_metrics(teachers: list[dict]) -> dict[str, int]:
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


def build_teacher_submission_response(
    teacher_id: int,
    date: str,
    dashboard: dict,
) -> dict:
    """提出データがなければダッシュボード行から逆変換した初期値を返す"""
    saved = get_teacher_submission(teacher_id, date)
    if saved is not None:
        return {"teacher_id": teacher_id, "date": date, "slots": saved}

    teacher = next((t for t in dashboard.get("teachers", []) if t["id"] == teacher_id), None)
    if teacher is None:
        raise HTTPException(
            status_code=404,
            detail=f"Teacher id={teacher_id} not found for date={date}",
        )
    slots = {
        str(i): dashboard_to_availability(teacher[f"s{i}"])
        for i in range(1, 5)
    }
    return {"teacher_id": teacher_id, "date": date, "slots": slots}
