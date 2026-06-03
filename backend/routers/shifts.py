from typing import Annotated

from fastapi import APIRouter, Query

from schemas.shifts import ShiftDashboardResponse
from services.data_loader import load_shift_dashboard

router = APIRouter(prefix="/api", tags=["shifts"])


@router.get("/shifts", response_model=ShiftDashboardResponse)
def get_shifts(
    date: Annotated[
        str | None,
        Query(description="対象日（YYYY-MM-DD）。省略時はモックの既定日を返す"),
    ] = None,
) -> ShiftDashboardResponse:
    """
    教室長ダッシュボード用のシフト一覧を返す。
    データ源: backend/data/shift-dashboard.json
    """
    payload = load_shift_dashboard(date=date)
    return ShiftDashboardResponse.model_validate(payload)
