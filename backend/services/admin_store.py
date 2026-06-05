import json
from copy import deepcopy

from fastapi import HTTPException

from config import DATA_DIR
from schemas.shifts import ShiftStatus

OVERRIDES_PATH = DATA_DIR / "admin-overrides.json"
_SLOT_FIELDS = ("s1", "s2", "s3", "s4")


def _load() -> dict[str, dict[str, dict[str, str]]]:
    if not OVERRIDES_PATH.is_file():
        return {}
    with OVERRIDES_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="admin-overrides.json must be an object")
    return data


def _save(data: dict[str, dict[str, dict[str, str]]]) -> None:
    OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OVERRIDES_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_overrides_for_date(date: str) -> dict[str, dict[str, str]]:
    return _load().get(date, {})


def set_slot_status(
    date: str,
    teacher_id: int,
    slot: int,
    status: ShiftStatus,
) -> None:
    store = _load()
    by_date = store.setdefault(date, {})
    by_teacher = by_date.setdefault(str(teacher_id), {})
    by_teacher[str(slot)] = status
    _save(store)


def confirm_all_pending(date: str, dashboard: dict) -> int:
    """待機のコマをすべて確定にする。変更したコマ数を返す。"""
    store = _load()
    by_date = store.setdefault(date, {})
    changed = 0
    for teacher in dashboard.get("teachers", []):
        tid = str(teacher["id"])
        by_teacher = by_date.setdefault(tid, {})
        for slot_num, field in enumerate(_SLOT_FIELDS, start=1):
            if teacher.get(field) == "待機":
                by_teacher[str(slot_num)] = "確定"
                changed += 1
    _save(store)
    return changed


def apply_admin_overrides(dashboard: dict) -> dict:
    result = deepcopy(dashboard)
    date = result.get("date")
    if not date:
        return result

    overrides = get_overrides_for_date(date)
    for teacher in result.get("teachers", []):
        tid = str(teacher["id"])
        teacher_overrides = overrides.get(tid)
        if not teacher_overrides:
            continue
        for slot_num, field in enumerate(_SLOT_FIELDS, start=1):
            key = str(slot_num)
            if key in teacher_overrides:
                teacher[field] = teacher_overrides[key]

    return result
