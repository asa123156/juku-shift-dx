"""年度（4月始まり）の通常授業用 Period を管理する。"""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Period as PeriodRow
from schemas.period import Period
from services.academic_calendar import (
    fiscal_year_bounds,
    fiscal_year_for_date,
    fiscal_year_label,
    open_dates_for_calendar_month,
    open_dates_for_fiscal_year,
)
from services.period_bootstrap import bootstrap_period_dashboards
from services.period_store import _to_schema


def _session() -> Session:
    return SessionLocal()


def find_regular_period_for_fiscal_year(fiscal_year: int) -> Period | None:
    start, end = fiscal_year_bounds(fiscal_year)
    with _session() as db:
        row = db.scalars(
            select(PeriodRow).where(
                PeriodRow.is_deleted == 0,
                PeriodRow.period_kind == "REGULAR",
                PeriodRow.start_date == date.fromisoformat(start),
                PeriodRow.end_date == date.fromisoformat(end),
            )
        ).first()
    if row is None:
        return None
    return _to_schema(row)


def find_regular_period_for_date(iso_date: str) -> Period | None:
    return find_regular_period_for_fiscal_year(fiscal_year_for_date(iso_date))


def ensure_fiscal_regular_period(
    fiscal_year: int,
    *,
    location_slug: str = "hakutei",
    closed_dates: list[str] | None = None,
) -> Period:
    """年度の通常授業コンテナ Period を取得または作成する。"""
    existing = find_regular_period_for_fiscal_year(fiscal_year)
    if existing is not None:
        if closed_dates is not None:
            return update_regular_period_closed_dates(existing.id, closed_dates)
        return existing

    start, end = fiscal_year_bounds(fiscal_year)
    closed = sorted(set(closed_dates or []))
    for iso in closed:
        d = date.fromisoformat(iso)
        if d < date.fromisoformat(start) or d > date.fromisoformat(end):
            raise HTTPException(status_code=400, detail=f"休校日 {iso} が年度外です")

    with _session() as db:
        row = PeriodRow(
            name=fiscal_year_label(fiscal_year),
            start_date=date.fromisoformat(start),
            end_date=date.fromisoformat(end),
            status="COLLECTING",
            closed_dates=closed,
            is_deleted=0,
            location_slug=location_slug,
            period_kind="REGULAR",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        period = _to_schema(row)

    bootstrap_period_dashboards(period.id)
    return period


def update_regular_period_closed_dates(period_id: int, closed_dates: list[str]) -> Period:
    with _session() as db:
        row = db.get(PeriodRow, period_id)
        if row is None or row.is_deleted or row.period_kind != "REGULAR":
            raise HTTPException(status_code=404, detail="年度通常 Period が見つかりません")
        period_start = row.start_date
        period_end = row.end_date
        cleaned: list[str] = []
        for iso in sorted(set(closed_dates)):
            d = date.fromisoformat(iso)
            if d < period_start or d > period_end:
                raise HTTPException(status_code=400, detail=f"休校日 {iso} が年度外です")
            if d.weekday() == 6:
                continue
            cleaned.append(iso)
        row.closed_dates = cleaned
        db.commit()
        db.refresh(row)
        return _to_schema(row)


def resolve_schedule_period_for_date(iso_date: str) -> Period:
    """通常授業・日次時間割用: 年度 REGULAR Period を返す（なければ自動作成）。"""
    fiscal_year = fiscal_year_for_date(iso_date)
    return ensure_fiscal_regular_period(fiscal_year)


def calendar_year_for_fiscal_month(fiscal_year: int, month: int) -> int:
    """年度内の暦月 → 西暦年（4-12月は fiscal_year、1-3月は fiscal_year+1）。"""
    return fiscal_year if month >= 4 else fiscal_year + 1


def build_calendar_month(fiscal_year: int, month: int) -> dict:
    period = ensure_fiscal_regular_period(fiscal_year)
    calendar_year = calendar_year_for_fiscal_month(fiscal_year, month)
    open_in_month = open_dates_for_calendar_month(calendar_year, month, period.closed_dates)
    start, end = fiscal_year_bounds(fiscal_year)
    return {
        "fiscal_year": fiscal_year,
        "calendar_year": calendar_year,
        "month": month,
        "period_id": period.id,
        "period_name": period.name,
        "fiscal_start_date": start,
        "fiscal_end_date": end,
        "open_dates": open_in_month,
        "open_count": len(open_in_month),
    }


def build_fiscal_year_summary(fiscal_year: int) -> dict:
    period = ensure_fiscal_regular_period(fiscal_year)
    open_dates = open_dates_for_fiscal_year(fiscal_year, period.closed_dates)
    start, end = fiscal_year_bounds(fiscal_year)
    with _session() as db:
        rows = db.scalars(
            select(PeriodRow).where(
                PeriodRow.is_deleted == 0,
                PeriodRow.period_kind == "CRAM",
                PeriodRow.end_date >= date.fromisoformat(start),
                PeriodRow.start_date <= date.fromisoformat(end),
            ).order_by(PeriodRow.start_date)
        ).all()
        cram_periods = [
            {
                "id": row.id,
                "name": row.name,
                "start_date": row.start_date.isoformat(),
                "end_date": row.end_date.isoformat(),
                "status": row.status,
            }
            for row in rows
        ]
    return {
        "fiscal_year": fiscal_year,
        "label": fiscal_year_label(fiscal_year),
        "start_date": start,
        "end_date": end,
        "regular_period_id": period.id,
        "regular_period_name": period.name,
        "open_days": len(open_dates),
        "closed_dates": period.closed_dates,
        "cram_periods": cram_periods,
    }


def ensure_current_fiscal_year() -> Period:
    return ensure_fiscal_regular_period(fiscal_year_for_date(date.today()))


def is_regular_period(period: Period) -> bool:
    return getattr(period, "period_kind", "CRAM") == "REGULAR"


def get_period_kind(period_id: int) -> str:
    from services.period_store import get_period

    period = get_period(period_id)
    return getattr(period, "period_kind", "CRAM")
