from copy import deepcopy

from services.admin_store import apply_admin_overrides
from services.data_loader import resolve_shift_date
from services.dashboard_store import load_shift_dashboard_base
from services.shift_store import apply_teacher_submissions, compute_metrics


def build_shift_dashboard(date: str | None = None) -> dict:
    resolved = resolve_shift_date(date)
    base = load_shift_dashboard_base(resolved)
    merged = apply_teacher_submissions(deepcopy(base))
    merged = apply_admin_overrides(merged)
    merged["metrics"] = compute_metrics(merged.get("teachers", []))
    return merged


def build_shift_dashboard_base_only(date: str | None = None) -> dict:
    resolved = resolve_shift_date(date)
    return load_shift_dashboard_base(resolved)
