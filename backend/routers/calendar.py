from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from services.academic_calendar import fiscal_year_for_date
from services.fiscal_year_store import build_calendar_month, build_fiscal_year_summary
from services.schedule_context import resolve_grid_period_ids, resolve_schedule_context

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


class ScheduleContextResponse(BaseModel):
    mode: str
    period_id: int
    period_kind: str
    period_name: str
    period_start_date: str
    period_end_date: str
    period_status: str
    fiscal_year: int
    calendar_year: int
    month: int
    regular_period_id: int
    cram_period_id: int | None = None


class GridPeriodContextResponse(BaseModel):
    date: str
    regular_period_id: int
    regular_period_name: str
    cram_period_id: int | None = None
    cram_period_name: str | None = None
    mode: str
    fiscal_year: int
    calendar_year: int
    month: int


class FiscalYearSummaryResponse(BaseModel):
    fiscal_year: int
    label: str
    start_date: str
    end_date: str
    regular_period_id: int
    regular_period_name: str
    open_days: int
    closed_dates: list[str] = Field(default_factory=list)
    cram_periods: list[dict] = Field(default_factory=list)


@router.get("/schedule-context", response_model=ScheduleContextResponse)
def get_schedule_context(
    date_param: Annotated[str | None, Query(alias="date", description="基準日 YYYY-MM-DD")] = None,
) -> ScheduleContextResponse:
    return ScheduleContextResponse.model_validate(resolve_schedule_context(date_param))


@router.get("/grid-context", response_model=GridPeriodContextResponse)
def get_grid_context(
    date_param: Annotated[str, Query(alias="date", description="対象日 YYYY-MM-DD")],
) -> GridPeriodContextResponse:
    return GridPeriodContextResponse.model_validate(resolve_grid_period_ids(date_param))


@router.get("/fiscal-year", response_model=FiscalYearSummaryResponse)
def get_fiscal_year(
    fiscal_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
) -> FiscalYearSummaryResponse:
    fy = fiscal_year if fiscal_year is not None else fiscal_year_for_date(date.today())
    return FiscalYearSummaryResponse.model_validate(build_fiscal_year_summary(fy))


@router.get("/month")
def get_calendar_month(
    fiscal_year: Annotated[int, Query(ge=2000, le=2100)],
    month: Annotated[int, Query(ge=1, le=12)],
) -> dict:
    return build_calendar_month(fiscal_year, month)
