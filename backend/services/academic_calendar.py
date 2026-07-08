"""4月始まりの年度（ fiscal year ）ユーティリティ。"""

from __future__ import annotations

from datetime import date

from services.period_store import iter_open_dates


def fiscal_year_for_date(iso_date: str | date) -> int:
    """暦日から年度（4月始まり）を返す。例: 2026-03-31 → 2025, 2026-04-01 → 2026"""
    d = iso_date if isinstance(iso_date, date) else date.fromisoformat(iso_date)
    return d.year if d.month >= 4 else d.year - 1


def fiscal_year_bounds(fiscal_year: int) -> tuple[str, str]:
    """年度の開始日・終了日（YYYY-MM-DD）。"""
    start = date(fiscal_year, 4, 1)
    end = date(fiscal_year + 1, 3, 31)
    return start.isoformat(), end.isoformat()


def fiscal_year_label(fiscal_year: int) -> str:
    return f"{fiscal_year}年度"


def open_dates_for_fiscal_year(
    fiscal_year: int,
    closed_dates: list[str] | None = None,
) -> list[str]:
    start, end = fiscal_year_bounds(fiscal_year)
    return iter_open_dates(start, end, closed_dates)


def open_dates_for_calendar_month(
    year: int,
    month: int,
    closed_dates: list[str] | None = None,
) -> list[str]:
    """指定暦月の開校日（日曜・休校日除外）。"""
    if month < 1 or month > 12:
        return []
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1)
        end = date.fromordinal(end.toordinal() - 1)
    return iter_open_dates(start.isoformat(), end.isoformat(), closed_dates)


def month_bounds(year: int, month: int) -> tuple[str, str]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        next_month = date(year, month + 1, 1)
        end = date.fromordinal(next_month.toordinal() - 1)
    return start.isoformat(), end.isoformat()
