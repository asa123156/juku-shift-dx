from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse

from schemas.admin import (
    AdminConfirmRequest,
    AdminConfirmResponse,
    AdminSlotUpdateRequest,
)
from schemas.assignment import (
    AssignmentCandidatesRequest,
    AssignmentCandidatesResponse,
    AssignmentCandidate,
    AutoAssignRequest,
    AutoAssignResponse,
    ImportAssignmentRequestsResponse,
)
from schemas.period import (
    PeriodCreateRequest,
    PeriodListResponse,
    PeriodResponse,
    PeriodStatusUpdateRequest,
    ShiftImportResponse,
)
from schemas.shifts import ShiftDashboardResponse
from services.admin_store import confirm_all_pending, set_slot_status
from services.assignment_engine import (
    get_assignment_candidates,
    rank_candidates,
    teachers_from_dashboard,
)
from services.assignment_store import get_assignments_for_date
from services.auto_assign import run_auto_assign
from services.csv_import import import_assignment_requests_from_csv
from services.dashboard_builder import build_shift_dashboard, build_shift_dashboard_base_only
from services.data_loader import resolve_shift_date
from services.period_store import create_period, get_period, iter_dates, list_periods, update_period_status
from services.shift_excel import export_shift_excel_csv, import_shift_excel_csv
from services.shift_store import ensure_teacher_exists

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.patch("/shifts/slot", response_model=ShiftDashboardResponse)
def admin_update_slot(body: AdminSlotUpdateRequest) -> ShiftDashboardResponse:
    """教室長が特定コマのステータスを直接変更する（確定・不足など）"""
    resolve_shift_date(body.date)
    dashboard = build_shift_dashboard_base_only(body.date)
    ensure_teacher_exists(dashboard, body.teacher_id)
    set_slot_status(body.date, body.teacher_id, body.slot, body.status)
    return ShiftDashboardResponse.model_validate(build_shift_dashboard(body.date))


@router.post("/shifts/confirm", response_model=AdminConfirmResponse)
def admin_confirm_shifts(body: AdminConfirmRequest) -> AdminConfirmResponse:
    """「シフトを確定する」: 当日の「待機」をすべて「確定」にする"""
    resolve_shift_date(body.date)
    preview = build_shift_dashboard(body.date)
    changed = confirm_all_pending(body.date, preview)
    dashboard = ShiftDashboardResponse.model_validate(build_shift_dashboard(body.date))
    return AdminConfirmResponse(
        date=body.date,
        confirmed_slots=changed,
        message=f"{changed} コマを確定しました",
        dashboard=dashboard,
    )


@router.post("/assignments/candidates", response_model=AssignmentCandidatesResponse)
def list_assignment_candidates(body: AssignmentCandidatesRequest) -> AssignmentCandidatesResponse:
    """指定生徒・科目に対する割当候補（NGルール適用後）を返す"""
    resolve_shift_date(body.date)
    dashboard = build_shift_dashboard(body.date)
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
    """
    未割当リクエストに対して自動割当を実行する。
    割当コマはダッシュボード上「AI提案」として反映される。
    """
    resolve_shift_date(body.date)
    proposals, assignments, dashboard = run_auto_assign(body.date)
    return AutoAssignResponse(
        date=body.date,
        message=f"{len(proposals)} 件の自動割当を提案しました",
        proposals=proposals,
        assignments=assignments,
        dashboard=ShiftDashboardResponse.model_validate(dashboard),
    )


@router.post("/assignment-requests/import", response_model=ImportAssignmentRequestsResponse)
async def import_assignment_requests(
    file: UploadFile = File(..., description="date,student_id,student_name,subject 形式の CSV"),
) -> ImportAssignmentRequestsResponse:
    """CSV から未割当リクエストを取り込む（同一 date+student+subject はスキップ）"""
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
    return PeriodResponse(
        period=period,
        dates=dates,
        message=f"期間ステータスを {body.status} に更新しました",
    )


@router.post("/shifts/import-excel", response_model=ShiftImportResponse)
async def import_shift_excel(
    period_id: int = Query(..., ge=1),
    file: UploadFile = File(..., description="role,entity_id,date,slot,symbol CSV"),
) -> ShiftImportResponse:
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
    count = import_shift_excel_csv(period_id, content)
    return ShiftImportResponse(
        period_id=period_id,
        imported_count=count,
        message=f"通常授業（◎）を {count} 件取り込みました",
    )


@router.get("/shifts/export-excel")
def export_shift_excel(period_id: int = Query(..., ge=1)) -> PlainTextResponse:
    get_period(period_id)
    csv_text = export_shift_excel_csv(period_id)
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="shift-period-{period_id}.csv"'},
    )
