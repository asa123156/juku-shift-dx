from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from schemas.admin import (
    AdminConfirmRequest,
    AdminConfirmResponse,
    AdminSlotUpdateRequest,
)
from schemas.assignment import (
    AssignmentCandidatesRequest,
    AssignmentCandidatesResponse,
    AssignmentCandidate,
    AssignmentGridResponse,
    AutoAssignRequest,
    AutoAssignResponse,
    ImportAssignmentRequestsResponse,
    ManualAssignRequest,
)
from schemas.period import (
    PeriodCreateRequest,
    PeriodListResponse,
    PeriodResponse,
    PeriodStatusUpdateRequest,
    ShiftImportResponse,
)
from schemas.shifts import ShiftDashboardResponse
from services.assignment_engine import (
    get_assignment_candidates,
    rank_candidates,
    teachers_from_dashboard,
)
from services.assignment_grid import build_assignment_grid, manual_assign
from services.assignment_store import get_assignments_for_date
from services.auto_assign import run_auto_assign
from services.availability_dashboard import build_availability_dashboard
from services.csv_import import import_assignment_requests_from_csv
from services.dashboard_builder import build_shift_dashboard, build_shift_dashboard_base_only
from services.data_loader import resolve_shift_date
from services.period_store import create_period, get_period, iter_dates, list_periods, update_period_status
from services.shift_excel import import_shift_excel_csv, import_shift_excel_xlsx, export_shift_excel_xlsx
from services.shift_store import ensure_teacher_exists

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/assignments/grid", response_model=AssignmentGridResponse)
def get_assignment_grid(date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$")) -> AssignmentGridResponse:
    """講師×コマの割当グリッド（自動・手動割当ページ用）"""
    resolve_shift_date(date)
    return AssignmentGridResponse.model_validate(build_assignment_grid(date))


@router.post("/assignments/manual", response_model=AssignmentGridResponse)
def assign_manual(body: ManualAssignRequest) -> AssignmentGridResponse:
    """手動で生徒を講師コマに割り当てる"""
    resolve_shift_date(body.date)
    grid = manual_assign(
        body.date,
        body.student_id,
        body.student_name,
        body.subject,
        body.teacher_id,
        body.slot,
    )
    return AssignmentGridResponse.model_validate(grid)


@router.patch("/shifts/slot", response_model=ShiftDashboardResponse)
def admin_update_slot(body: AdminSlotUpdateRequest) -> ShiftDashboardResponse:
    resolve_shift_date(body.date)
    dashboard = build_shift_dashboard_base_only(body.date)
    ensure_teacher_exists(dashboard, body.teacher_id)
    from services.admin_store import set_slot_status

    set_slot_status(body.date, body.teacher_id, body.slot, body.status)
    return ShiftDashboardResponse.model_validate(build_availability_dashboard(body.date))


@router.post("/shifts/confirm", response_model=AdminConfirmResponse)
def admin_confirm_shifts(body: AdminConfirmRequest) -> AdminConfirmResponse:
    resolve_shift_date(body.date)
    preview = build_availability_dashboard(body.date)
    return AdminConfirmResponse(
        date=body.date,
        confirmed_slots=0,
        message="シフト確定は「シフト確定」ボタン（期間を FINALIZED）で行ってください",
        dashboard=ShiftDashboardResponse.model_validate(preview),
    )


@router.post("/assignments/candidates", response_model=AssignmentCandidatesResponse)
def list_assignment_candidates(body: AssignmentCandidatesRequest) -> AssignmentCandidatesResponse:
    resolve_shift_date(body.date)
    dashboard = build_availability_dashboard(body.date)
    teacher_list = teachers_from_dashboard(dashboard)
    current_assignments = get_assignments_for_date(body.date)

    raw = get_assignment_candidates(
        student_id=body.student_id,
        subject=body.subject,
        teacher_list=teacher_list,
        current_assignments=current_assignments,
        date=body.date,
    )
    ranked = rank_candidates(raw, teacher_list)
    candidates = [AssignmentCandidate.model_validate(c) for c in ranked]

    return AssignmentCandidatesResponse(
        date=body.date,
        student_id=body.student_id,
        subject=body.subject,
        candidates=candidates,
    )


@router.post("/auto-assign", response_model=AutoAssignResponse)
def auto_assign(body: AutoAssignRequest) -> AutoAssignResponse:
    resolve_shift_date(body.date)
    proposals, assignments, grid = run_auto_assign(body.date)
    return AutoAssignResponse(
        date=body.date,
        message=f"{len(proposals)} 件の自動割当を実行しました",
        proposals=proposals,
        assignments=assignments,
        grid=AssignmentGridResponse.model_validate(grid),
    )


@router.post("/assignment-requests/import", response_model=ImportAssignmentRequestsResponse)
async def import_assignment_requests(
    file: UploadFile = File(..., description="date,student_id,student_name,subject 形式の CSV"),
) -> ImportAssignmentRequestsResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV ファイルを指定してください")

    raw = await file.read()
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            content = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            content = None
    if content is None:
        raise HTTPException(status_code=400, detail="CSV の文字コードを判別できません")

    imported, skipped, by_date = import_assignment_requests_from_csv(content)
    return ImportAssignmentRequestsResponse(
        imported_count=imported,
        skipped_count=skipped,
        by_date=by_date,
        message=f"{imported} 件を取り込みました（重複 {skipped} 件スキップ）",
    )


@router.get("/periods", response_model=PeriodListResponse)
def get_periods() -> PeriodListResponse:
    periods, active_id = list_periods()
    return PeriodListResponse(periods=periods, active_period_id=active_id)


@router.post("/periods", response_model=PeriodResponse)
def create_shift_period(body: PeriodCreateRequest) -> PeriodResponse:
    period = create_period(body.name, body.start_date, body.end_date)
    dates = iter_dates(period.start_date, period.end_date)
    return PeriodResponse(
        period=period,
        dates=dates,
        message=f"期間「{period.name}」を DRAFT で作成しました",
    )


@router.patch("/periods/{period_id}/status", response_model=PeriodResponse)
def change_period_status(period_id: int, body: PeriodStatusUpdateRequest) -> PeriodResponse:
    period = update_period_status(period_id, body.status)
    dates = iter_dates(period.start_date, period.end_date)
    msg = f"期間ステータスを {body.status} に更新しました"
    if body.status == "FINALIZED":
        msg = "シフトを確定しました。生徒に確定スケジュールが反映されます。"
    return PeriodResponse(period=period, dates=dates, message=msg)


@router.post("/shifts/import-excel", response_model=ShiftImportResponse)
async def import_shift_excel(
    period_id: int = Query(..., ge=1),
    file: UploadFile = File(..., description="role,entity_id,date,slot,symbol Excel/CSV"),
) -> ShiftImportResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="ファイルを指定してください")
    raw = await file.read()
    lower = file.filename.lower()
    if lower.endswith(".xlsx"):
        count = import_shift_excel_xlsx(period_id, raw)
    elif lower.endswith(".csv"):
        for encoding in ("utf-8-sig", "utf-8", "cp932"):
            try:
                content = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                content = None
        if content is None:
            raise HTTPException(status_code=400, detail="CSV の文字コードを判別できません")
        count = import_shift_excel_csv(period_id, content)
    else:
        raise HTTPException(status_code=400, detail="Excel (.xlsx) または CSV ファイルを指定してください")

    return ShiftImportResponse(
        period_id=period_id,
        imported_count=count,
        message=f"通常授業（◎）を {count} 件取り込みました（シフト確定後にダッシュボードへ反映）",
    )


@router.get("/shifts/export-excel")
def export_shift_excel(period_id: int = Query(..., ge=1)) -> Response:
    get_period(period_id)
    xlsx_bytes = export_shift_excel_xlsx(period_id)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="shift-period-{period_id}.xlsx"'},
    )
