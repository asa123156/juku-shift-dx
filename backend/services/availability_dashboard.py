from copy import deepcopy

from services.dashboard_builder import build_shift_dashboard_base_only
from services.period_store import find_period_for_date
from services.shift_store import apply_teacher_submissions, compute_metrics
from services.slot_timing import SLOT_NUMS, generate_time_slots

AvailabilitySymbol = str  # "×" | "" | "通常授業"


def to_availability_symbol(status: str) -> AvailabilitySymbol:
    if status in ("通常授業", "◎"):
        return "通常授業"
    if status in ("不可", "×"):
        return "×"
    return ""


def build_availability_dashboard(iso_date: str) -> dict:
    """講師シフト（空き/×）を返す。通常授業は時間割表の割当で表示。"""
    base = build_shift_dashboard_base_only(iso_date)
    merged = apply_teacher_submissions(deepcopy(base))

    period = find_period_for_date(iso_date)
    finalized = period is not None and period.status == "FINALIZED"

    merged["metrics"] = compute_metrics(merged.get("teachers", []))

    for teacher in merged.get("teachers", []):
        for slot_num in SLOT_NUMS:
            field = f"s{slot_num}"
            teacher[field] = to_availability_symbol(teacher.get(field, ""))

    merged["time_slots"] = generate_time_slots()
    merged["period_status"] = period.status if period else None
    merged["finalized"] = finalized
    return merged
