import json
from copy import deepcopy

from fastapi import HTTPException

from config import DATA_DIR
from schemas.period import SlotSymbol, empty_slots
from schemas.shifts import ShiftStatus

SUBMISSIONS_PATH = DATA_DIR / "teacher-submissions.json"

SYMBOL_TO_DASHBOARD: dict[SlotSymbol, ShiftStatus] = {
    "◎": "通常授業",
    "×": "不可",
    "": "待機",
}

LEGACY_TO_SYMBOL: dict[str, SlotSymbol] = {
    "regular_class": "◎",
    "unavailable": "×",
    "available": "",
    "blank": "",
    "priority": "◎",
}

_SLOT_FIELDS = ("s1", "s2", "s3", "s4")


def symbol_to_dashboard(status: SlotSymbol) -> ShiftStatus:
    return SYMBOL_TO_DASHBOARD[status]


def dashboard_to_symbol(status: ShiftStatus) -> SlotSymbol:
    if status == "通常授業":
        return "◎"
    if status == "不可":
        return "×"
    if status in ("待機", "確定", "AI提案"):
        return ""
    return ""


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


def _write_submissions_file(data: dict[str, dict[str, dict[str, str]]]) -> None:
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


def get_teacher_submission(teacher_id: int, iso_date: str) -> dict[str, SlotSymbol] | None:
    store = _load_submissions_file()
    raw = store.get(iso_date, {}).get(str(teacher_id))
    if raw is None:
        return None
    return _normalize_slots(raw)


def save_teacher_submission(
    teacher_id: int,
    iso_date: str,
    slots: dict[str, SlotSymbol],
) -> dict[str, ShiftStatus]:
    store = _load_submissions_file()
    existing = store.get(iso_date, {}).get(str(teacher_id), {})
    merged = {**existing, **slots}
    store.setdefault(iso_date, {})[str(teacher_id)] = merged
    _write_submissions_file(store)
    return {
        f"s{i}": symbol_to_dashboard(_normalize_slots(merged)[str(i)])
        for i in range(1, 5)
    }


def save_teacher_bulk(teacher_id: int, submissions: list[dict]) -> list[str]:
    saved: list[str] = []
    for row in submissions:
        iso_date = row["date"]
        save_teacher_submission(teacher_id, iso_date, row["slots"])
        saved.append(iso_date)
    return saved


def update_single_slot(
    teacher_id: int,
    iso_date: str,
    slot: int,
    status: SlotSymbol,
) -> dict[str, ShiftStatus]:
    current = get_teacher_submission(teacher_id, iso_date) or empty_slots()
    current[str(slot)] = status
    return save_teacher_submission(teacher_id, iso_date, current)


def apply_teacher_submissions(dashboard: dict) -> dict:
    result = deepcopy(dashboard)
    iso_date = result.get("date")
    if not iso_date:
        return result

    store = _load_submissions_file()
    by_date = store.get(iso_date, {})

    for teacher in result.get("teachers", []):
        submitted = by_date.get(str(teacher["id"]))
        if not submitted:
            continue
        slots = _normalize_slots(submitted)
        for slot_num, field in enumerate(_SLOT_FIELDS, start=1):
            teacher[field] = symbol_to_dashboard(slots[str(slot_num)])

    return result


def build_teacher_submission_response(
    teacher_id: int,
    iso_date: str,
    dashboard: dict,
) -> dict:
    saved = get_teacher_submission(teacher_id, iso_date)
    if saved is not None:
        return {"teacher_id": teacher_id, "date": iso_date, "slots": saved}

    teacher = next((t for t in dashboard.get("teachers", []) if t["id"] == teacher_id), None)
    if teacher is None:
        raise HTTPException(
            status_code=404,
            detail=f"Teacher id={teacher_id} not found for date={iso_date}",
        )
    slots = {str(i): dashboard_to_symbol(teacher[f"s{i}"]) for i in range(1, 5)}
    return {"teacher_id": teacher_id, "date": iso_date, "slots": slots}


def ensure_teacher_exists(dashboard: dict, teacher_id: int) -> None:
    teacher_ids = {t["id"] for t in dashboard.get("teachers", [])}
    if teacher_id not in teacher_ids:
        raise HTTPException(status_code=404, detail=f"Teacher id={teacher_id} not found")
