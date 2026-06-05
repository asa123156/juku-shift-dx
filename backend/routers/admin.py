from fastapi import APIRouter

from schemas.admin import (
    AdminConfirmRequest,
    AdminConfirmResponse,
    AdminSlotUpdateRequest,
)
from schemas.shifts import ShiftDashboardResponse
from services.admin_store import confirm_all_pending, set_slot_status
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
