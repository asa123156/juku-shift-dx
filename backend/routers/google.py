from fastapi import APIRouter

from schemas.google import (
    GoogleSheetExportRequest,
    GoogleSheetExportResponse,
    GoogleSheetImportRequest,
    GoogleSheetImportResponse,
    GoogleStatusResponse,
)
from services.google_schedule_sync import export_to_google_sheet, import_from_google_sheet
from services.google_sheets import get_service_account_email, is_google_configured

router = APIRouter(prefix="/api/google", tags=["google"])


@router.get("/status", response_model=GoogleStatusResponse)
def google_status() -> GoogleStatusResponse:
    configured = is_google_configured()
    service_account_email = get_service_account_email()
    if configured:
        msg = "Google Sheets 連携が利用可能です（サービスアカウント設定済み）"
        if service_account_email:
            msg += f" 共有先: {service_account_email}"
    else:
        msg = (
            "Google Sheets 連携は未設定です。"
            "GOOGLE_SERVICE_ACCOUNT_FILE または GOOGLE_SERVICE_ACCOUNT_JSON を設定してください。"
        )
    return GoogleStatusResponse(
        configured=configured,
        message=msg,
        service_account_email=service_account_email,
    )


@router.post("/import", response_model=GoogleSheetImportResponse)
def import_google_sheet(body: GoogleSheetImportRequest) -> GoogleSheetImportResponse:
    stats = import_from_google_sheet(
        body.period_id,
        body.spreadsheet_ref,
        iso_date=body.date,
        sheet_name=body.sheet_name,
    )
    return GoogleSheetImportResponse(**stats)


@router.post("/export", response_model=GoogleSheetExportResponse)
def export_google_sheet(body: GoogleSheetExportRequest) -> GoogleSheetExportResponse:
    result = export_to_google_sheet(
        body.period_id,
        body.spreadsheet_ref,
        title=body.title,
    )
    return GoogleSheetExportResponse(**result)
