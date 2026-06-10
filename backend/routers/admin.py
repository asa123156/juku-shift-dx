from fastapi import APIRouter

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
from services.dashboard_builder import build_shift_dashboard, build_shift_dashboard_base_only
from services.data_loader import resolve_shift_date
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
