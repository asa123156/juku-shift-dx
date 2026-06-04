from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from schemas.shifts import (
    ShiftDashboardResponse,
    ShiftSlotUpdateRequest,
    ShiftSubmitRequest,
    ShiftSubmitResponse,
    TeacherShiftSubmissionResponse,
)
from services.data_loader import load_shift_dashboard
from services.shift_store import (
    build_teacher_submission_response,
    save_teacher_submission,
    update_single_slot,
)

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
    講師の提出データ（teacher-submissions.json）があれば該当行に反映する。
    """
    payload = load_shift_dashboard(date=date)
    return ShiftDashboardResponse.model_validate(payload)


@router.get("/shifts/me", response_model=TeacherShiftSubmissionResponse)
def get_my_shift(
    teacher_id: Annotated[int, Query(ge=1, description="ログイン講師ID（開発中は 1 など）")],
    date: Annotated[
        str | None,
        Query(description="対象日。省略時は shift-dashboard.json の date"),
    ] = None,
) -> TeacherShiftSubmissionResponse:
    """
    講師シフト入力画面用。コマごとの available / unavailable / blank を返す。
    未提出の場合はダッシュボード行から推定した初期値を返す。
    """
    dashboard = load_shift_dashboard(date=date, apply_submissions=False)
    resolved_date = dashboard["date"]
    if date is not None and date != resolved_date:
        raise HTTPException(status_code=404, detail=f"No shift data for date={date}")

    payload = build_teacher_submission_response(teacher_id, resolved_date, dashboard)
    return TeacherShiftSubmissionResponse.model_validate(payload)


@router.post("/shifts", response_model=ShiftSubmitResponse)
def submit_shifts(body: ShiftSubmitRequest) -> ShiftSubmitResponse:
    """
    講師が1日分のシフトを提出する（フロントの「提出する」ボタン用）。
    教室長ダッシュボードでは ○→待機、×→不可、未入力→未提出 に変換される。
    """
    dashboard = load_shift_dashboard(date=body.date, apply_submissions=False)
    if dashboard.get("date") != body.date:
        raise HTTPException(status_code=404, detail=f"No shift data for date={body.date}")

    teacher_ids = {t["id"] for t in dashboard.get("teachers", [])}
    if body.teacher_id not in teacher_ids:
        raise HTTPException(status_code=404, detail=f"Teacher id={body.teacher_id} not found")

    dashboard_status = save_teacher_submission(body.teacher_id, body.date, body.slots)
    return ShiftSubmitResponse(
        teacher_id=body.teacher_id,
        date=body.date,
        message="シフトを提出しました",
        dashboard_status=dashboard_status,
    )


@router.patch("/shifts", response_model=ShiftSubmitResponse)
def patch_shift_slot(body: ShiftSlotUpdateRequest) -> ShiftSubmitResponse:
    """1コマだけ更新する（オプション。フロントがコマ単位で送る場合）"""
    dashboard = load_shift_dashboard(date=body.date, apply_submissions=False)
    if dashboard.get("date") != body.date:
        raise HTTPException(status_code=404, detail=f"No shift data for date={body.date}")

    teacher_ids = {t["id"] for t in dashboard.get("teachers", [])}
    if body.teacher_id not in teacher_ids:
        raise HTTPException(status_code=404, detail=f"Teacher id={body.teacher_id} not found")

    dashboard_status = update_single_slot(
        body.teacher_id, body.date, body.slot, body.status
    )
    return ShiftSubmitResponse(
        teacher_id=body.teacher_id,
        date=body.date,
        message="コマを更新しました",
        dashboard_status=dashboard_status,
    )
