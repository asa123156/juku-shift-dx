from copy import deepcopy

from services.dashboard_builder import build_shift_dashboard_base_only
from services.period_store import find_period_for_date, get_entity_base_day
from services.shift_store import apply_teacher_submissions, compute_metrics
from services.slot_timing import generate_time_slots

AvailabilitySymbol = str  # "◎" | "×" | ""


def to_availability_symbol(status: str) -> AvailabilitySymbol:
    if status in ("通常授業", "◎"):
        return "◎"
    if status in ("不可", "×"):
        return "×"
    return ""


def build_availability_dashboard(iso_date: str) -> dict:
    """講師シフトを ◎ / × / 空 の3値だけで返す。Excel ◎ は FINALIZED 時のみ反映。"""
    base = build_shift_dashboard_base_only(iso_date)
    merged = apply_teacher_submissions(deepcopy(base))

    period = find_period_for_date(iso_date)
    finalized = period is not None and period.status == "FINALIZED"

    merged["metrics"] = compute_metrics(merged.get("teachers", []))

    if finalized and period is not None:
        for teacher in merged.get("teachers", []):
            tid = teacher["id"]
            for slot_num in range(1, 5):
                day = get_entity_base_day(period.id, "teacher", tid, iso_date)
                if day[str(slot_num)] == "◎":
                    teacher[f"s{slot_num}"] = "◎"

    for teacher in merged.get("teachers", []):
        for slot_num in range(1, 5):
            field = f"s{slot_num}"
            teacher[field] = to_availability_symbol(teacher.get(field, ""))

    merged["time_slots"] = generate_time_slots()
    merged["period_status"] = period.status if period else None
    merged["finalized"] = finalized
    return merged
