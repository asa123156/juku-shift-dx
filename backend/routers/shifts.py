from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from config import DEFAULT_SHIFT_DATE
from schemas.admin import ShiftDatesResponse, TeacherListItem
from schemas.shifts import (
    ShiftDashboardResponse,
    ShiftSlotUpdateRequest,
    ShiftSubmitRequest,
    ShiftSubmitResponse,
    TeacherShiftSubmissionResponse,
)
from services.dashboard_builder import build_shift_dashboard, build_shift_dashboard_base_only
from services.data_loader import list_shift_dates, resolve_shift_date
from services.shift_store import (
    build_teacher_submission_response,
    ensure_teacher_exists,
    save_teacher_submission,
    update_single_slot,
)

router = APIRouter(prefix="/api", tags=["shifts"])


@router.get("/shifts/dates", response_model=ShiftDatesResponse)
def get_shift_dates() -> ShiftDatesResponse:
    dates = list_shift_dates()
    default = DEFAULT_SHIFT_DATE if DEFAULT_SHIFT_DATE in dates else (dates[0] if dates else DEFAULT_SHIFT_DATE)
    return ShiftDatesResponse(dates=dates, default_date=default)


@router.get("/shifts/teachers", response_model=list[TeacherListItem])
def list_teachers(
    date: Annotated[str | None, Query(description="対象日 YYYY-MM-DD")] = None,
) -> list[TeacherListItem]:
    dashboard = build_shift_dashboard_base_only(date)
    return [
        TeacherListItem(id=t["id"], name=t["name"], color=t["color"])
        for t in dashboard.get("teachers", [])
    ]


@router.get("/shifts", response_model=ShiftDashboardResponse)
def get_shifts(
    date: Annotated[
        str | None,
        Query(description="対象日（YYYY-MM-DD）。省略時は既定日"),
    ] = None,
) -> ShiftDashboardResponse:
    payload = build_shift_dashboard(date)
    return ShiftDashboardResponse.model_validate(payload)


@router.get("/shifts/me", response_model=TeacherShiftSubmissionResponse)
def get_my_shift(
    teacher_id: Annotated[int, Query(ge=1, description="ログイン講師ID")],
    date: Annotated[str | None, Query(description="対象日 YYYY-MM-DD")] = None,
) -> TeacherShiftSubmissionResponse:
    resolved = resolve_shift_date(date)
    dashboard = build_shift_dashboard_base_only(resolved)
    payload = build_teacher_submission_response(teacher_id, resolved, dashboard)
    return TeacherShiftSubmissionResponse.model_validate(payload)


@router.post("/shifts", response_model=ShiftSubmitResponse)
def submit_shifts(body: ShiftSubmitRequest) -> ShiftSubmitResponse:
    resolve_shift_date(body.date)
    dashboard = build_shift_dashboard_base_only(body.date)
    ensure_teacher_exists(dashboard, body.teacher_id)

    dashboard_status = save_teacher_submission(body.teacher_id, body.date, body.slots)
    return ShiftSubmitResponse(
        teacher_id=body.teacher_id,
        date=body.date,
        message="シフトを提出しました",
        dashboard_status=dashboard_status,
    )


@router.patch("/shifts", response_model=ShiftSubmitResponse)
def patch_shift_slot(body: ShiftSlotUpdateRequest) -> ShiftSubmitResponse:
    resolve_shift_date(body.date)
    dashboard = build_shift_dashboard_base_only(body.date)
    ensure_teacher_exists(dashboard, body.teacher_id)

    dashboard_status = update_single_slot(
        body.teacher_id, body.date, body.slot, body.status
    )
    return ShiftSubmitResponse(
        teacher_id=body.teacher_id,
        date=body.date,
        message="コマを更新しました",
        dashboard_status=dashboard_status,
    )
