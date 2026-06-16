from fastapi import APIRouter, Query
from fastapi.responses import Response

from services.juku_grid_export import export_period_schedule_workbook
from services.period_store import get_period

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/juku-schedule")
def download_juku_schedule(
    period_id: int = Query(..., ge=1, description="講習期間 ID"),
) -> Response:
    """インポート済み月次 Excel に割当を反映して返す。"""
    period = get_period(period_id)
    xlsx_bytes, original_name = export_period_schedule_workbook(period_id)
    safe = original_name.replace('"', "")
    filename = safe if safe.lower().endswith((".xlsx", ".xlsm")) else f"{period.name}_時間割.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
