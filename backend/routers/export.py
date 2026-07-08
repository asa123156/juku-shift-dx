from urllib.parse import quote

from fastapi import APIRouter, Query
from fastapi.responses import Response
from pydantic import BaseModel

from services.juku_grid_export import (
    export_calendar_month_workbook,
    export_period_schedule_workbook,
    save_schedule_to_output_folder,
)
from services.location_config import list_locations
from services.period_store import get_period
from services.proposal_export import export_period_proposals_xlsx, export_student_proposal_xlsx

router = APIRouter(prefix="/api/export", tags=["export"])


def _attachment_headers(filename: str) -> dict[str, str]:
    """日本語ファイル名でも Starlette が latin-1 エラーにならない Content-Disposition。"""
    cleaned = filename.replace('"', "")
    ascii_fallback = "download.xlsx"
    if cleaned.lower().endswith((".xlsx", ".xlsm")):
        ascii_fallback = "schedule.xlsx" if cleaned.endswith(".xlsx") else "schedule.xlsm"
    encoded = quote(cleaned)
    return {
        "Content-Disposition": (
            f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded}'
        ),
    }


class LocationItem(BaseModel):
    slug: str
    name: str
    description: str = ""
    default: bool = False


class LocationListResponse(BaseModel):
    locations: list[LocationItem]


class ScheduleSaveResponse(BaseModel):
    period_id: int
    location_slug: str
    output_dir: str
    file_path: str
    message: str


@router.get("/locations", response_model=LocationListResponse)
def get_export_locations() -> LocationListResponse:
    """時間割出力形式（拠点）一覧。"""
    return LocationListResponse(locations=[LocationItem.model_validate(loc) for loc in list_locations()])


@router.get("/juku-schedule")
def download_juku_schedule(
    period_id: int | None = Query(None, ge=1, description="講習期間または年度 Period ID"),
    calendar_year: int | None = Query(None, ge=2000, le=2100, description="暦年（月次出力）"),
    month: int | None = Query(None, ge=1, le=12, description="月（月次出力）"),
    location: str | None = Query(None, description="拠点 slug（省略時は Period の設定）"),
) -> Response:
    """DB 正本（assignments）を拠点形式の Excel に変換して返す。"""
    if calendar_year is not None and month is not None:
        xlsx_bytes, filename = export_calendar_month_workbook(calendar_year, month, location)
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=_attachment_headers(filename),
        )
    if period_id is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="period_id または calendar_year+month を指定してください")
    period = get_period(period_id)
    xlsx_bytes, filename = export_period_schedule_workbook(period_id, location)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=_attachment_headers(filename),
    )


@router.post("/juku-schedule/save", response_model=ScheduleSaveResponse)
def save_juku_schedule_to_folder(
    period_id: int = Query(..., ge=1, description="講習期間 ID"),
    location: str | None = Query(None, description="拠点 slug（省略時は講習期間の設定）"),
) -> ScheduleSaveResponse:
    """DB 正本を backend/output/{拠点}/{期間}/ に書き出す。"""
    get_period(period_id)
    result = save_schedule_to_output_folder(period_id, location)
    return ScheduleSaveResponse.model_validate(result)


@router.get("/student-proposal")
def download_student_proposal(
    period_id: int = Query(..., ge=1),
    student_id: int = Query(..., ge=1),
) -> Response:
    """時間割表（assignments 正本）から生徒別提案書 Excel を返す。"""
    get_period(period_id)
    xlsx_bytes, filename = export_student_proposal_xlsx(period_id, student_id)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=_attachment_headers(filename),
    )


@router.get("/student-proposals")
def download_period_proposals(
    period_id: int = Query(..., ge=1),
) -> Response:
    """時間割表を正本とした提案書 Excel（全生徒・シート分割）。"""
    get_period(period_id)
    xlsx_bytes, filename = export_period_proposals_xlsx(period_id)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=_attachment_headers(filename),
    )
