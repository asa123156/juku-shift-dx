from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from config import DEFAULT_SHIFT_DATE
from schemas.admin import ShiftDatesResponse, TeacherListItem
from schemas.period import BulkShiftSubmitRequest, BulkShiftSubmitResponse, MyScheduleResponse
from schemas.shifts import (
    ShiftDashboardResponse,
    ShiftSlotUpdateRequest,
    ShiftSubmitRequest,
    ShiftSubmitResponse,
    TeacherShiftSubmissionResponse,
)
from services.dashboard_builder import build_shift_dashboard, build_shift_dashboard_base_only
from services.data_loader import list_shift_dates, resolve_shift_date
from services.period_store import find_period_for_date
from services.schedule_service import bulk_save_submissions, build_my_schedule
from services.shift_store import (
    build_teacher_submission_response,
    ensure_teacher_exists,
    save_teacher_submission,
    update_single_slot,
)

router = APIRouter(prefix="/api", tags=["shifts"])


def _period_meta(iso_date: str) -> dict:
    period = find_period_for_date(iso_date)
    if period is None:
        return {}
    return {
        "period_id": period.id,
        "period_status": period.status,
        "readonly": period.status == "FINALIZED",
    }


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
    date: Annotated[str | None, Query(description="対象日（YYYY-MM-DD）。省略時は既定日")] = None,
) -> ShiftDashboardResponse:
    payload = build_shift_dashboard(date)
    return ShiftDashboardResponse.model_validate(payload)


@router.get("/shifts/me", response_model=TeacherShiftSubmissionResponse)
def get_my_shift(
    teacher_id: Annotated[int, Query(ge=1, description="ログイン講師ID")],
    date: Annotated[str | None, Query(description="対象日 YYYY-MM-DD")] = None,
) -> TeacherShiftSubmissionResponse:
    resolved = resolve_shift_date(date)
    period = find_period_for_date(resolved)
    if period is not None:
        schedule = build_my_schedule("teacher", teacher_id, period.id)
        day = next((d for d in schedule["dates"] if d["date"] == resolved), None)
        if day:
            return TeacherShiftSubmissionResponse(
                teacher_id=teacher_id,
                date=resolved,
                slots=day["slots"],
                period_id=period.id,
                period_status=period.status,
                readonly=day["readonly"],
                locked_slots=day["locked_slots"],
            )
    dashboard = build_shift_dashboard_base_only(resolved)
    payload = build_teacher_submission_response(teacher_id, resolved, dashboard)
    return TeacherShiftSubmissionResponse.model_validate({**payload, **_period_meta(resolved)})


@router.get("/shifts/my-schedule", response_model=MyScheduleResponse)
def get_my_schedule(
    role: Annotated[str, Query(pattern="^(teacher|student)$")],
    entity_id: Annotated[int, Query(ge=1)],
    period_id: Annotated[int, Query(ge=1)],
) -> MyScheduleResponse:
    payload = build_my_schedule(role, entity_id, period_id)
    return MyScheduleResponse.model_validate(payload)


@router.post("/shifts", response_model=ShiftSubmitResponse)
def submit_shifts(body: ShiftSubmitRequest) -> ShiftSubmitResponse:
    resolve_shift_date(body.date)
    period = find_period_for_date(body.date)
    if period is not None:
        if period.status == "FINALIZED":
            raise HTTPException(status_code=409, detail="確定済みのため提出できません")
        if period.status == "COLLECTING":
            bulk_save_submissions(
                "teacher",
                body.teacher_id,
                period.id,
                [{"date": body.date, "slots": body.slots}],
            )
            merged = build_my_schedule("teacher", body.teacher_id, period.id)
            day = next(d for d in merged["dates"] if d["date"] == body.date)
            from services.shift_store import symbol_to_dashboard

            dashboard_status = {
                f"s{i}": symbol_to_dashboard(day["slots"][str(i)]) for i in range(1, 5)
            }
            return ShiftSubmitResponse(
                teacher_id=body.teacher_id,
                date=body.date,
                message="シフトを提出しました",
                dashboard_status=dashboard_status,
            )
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
    period = find_period_for_date(body.date)
    if period is not None and period.status == "FINALIZED":
        raise HTTPException(status_code=409, detail="確定済みのため編集できません")
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


@router.patch("/shifts/bulk", response_model=BulkShiftSubmitResponse)
def bulk_submit_shifts(body: BulkShiftSubmitRequest) -> BulkShiftSubmitResponse:
    saved = bulk_save_submissions(
        body.role,
        body.entity_id,
        body.period_id,
        [s.model_dump() for s in body.submissions],
    )
    return BulkShiftSubmitResponse(
        role=body.role,
        entity_id=body.entity_id,
        period_id=body.period_id,
        saved_dates=saved,
        message=f"{len(saved)} 日分を保存しました",
    )
