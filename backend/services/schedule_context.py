"""生徒・講師・管理画面向けのスケジュール文脈（講習 vs 通常）を解決する。"""

from __future__ import annotations

from datetime import date

from services.academic_calendar import fiscal_year_for_date
from services.fiscal_year_store import resolve_schedule_period_for_date
from services.period_store import find_cram_period_for_date, get_period, list_periods


def _resolve_cram_period_for_user(iso_date: str):
    """講習 Period: 管理中の active CRAM を優先し、なければ当日を含む CRAM。"""
    _, active_id = list_periods()
    if active_id is not None:
        try:
            active = get_period(active_id)
            if (
                getattr(active, "period_kind", "CRAM") == "CRAM"
                and active.status in ("COLLECTING", "FINALIZED")
            ):
                return active
        except Exception:
            pass
    return find_cram_period_for_date(iso_date)


def resolve_schedule_context(iso_date: str | None = None) -> dict:
    """指定日のスケジュール表示モードと period_id を返す。"""
    target = iso_date or date.today().isoformat()
    regular = resolve_schedule_period_for_date(target)
    cram = _resolve_cram_period_for_user(target)
    fiscal_year = fiscal_year_for_date(target)
    calendar_year = int(target[:4])
    month = int(target[5:7])

    if cram is not None and cram.status in ("COLLECTING", "FINALIZED"):
        return {
            "mode": "cram",
            "period_id": cram.id,
            "period_kind": "CRAM",
            "period_name": cram.name,
            "period_start_date": cram.start_date,
            "period_end_date": cram.end_date,
            "period_status": cram.status,
            "fiscal_year": fiscal_year,
            "calendar_year": calendar_year,
            "month": month,
            "regular_period_id": regular.id,
            "cram_period_id": cram.id,
        }

    return {
        "mode": "regular",
        "period_id": regular.id,
        "period_kind": "REGULAR",
        "period_name": regular.name,
        "period_start_date": regular.start_date,
        "period_end_date": regular.end_date,
        "period_status": regular.status,
        "fiscal_year": fiscal_year,
        "calendar_year": calendar_year,
        "month": month,
        "regular_period_id": regular.id,
        "cram_period_id": None,
    }


def resolve_grid_period_ids(iso_date: str) -> dict:
    """時間割表: 通常授業用 REGULAR と講習用 CRAM の period_id。"""
    ctx = resolve_schedule_context(iso_date)
    regular = resolve_schedule_period_for_date(iso_date)
    cram = find_cram_period_for_date(iso_date)
    return {
        "date": iso_date,
        "regular_period_id": regular.id,
        "regular_period_name": regular.name,
        "cram_period_id": cram.id if cram is not None else None,
        "cram_period_name": cram.name if cram is not None else None,
        "mode": ctx["mode"],
        "fiscal_year": ctx["fiscal_year"],
        "calendar_year": ctx["calendar_year"],
        "month": ctx["month"],
    }


def tutoring_period_id_for_date(iso_date: str, regular_period_id: int) -> int:
    """講習枠の保存先 period_id。講習期間中は CRAM、それ以外は REGULAR。"""
    cram = find_cram_period_for_date(iso_date)
    if cram is not None and cram.status in ("COLLECTING", "FINALIZED"):
        return cram.id
    return regular_period_id
