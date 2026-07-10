from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from dependencies import get_current_user, require_admin
from schemas.admin import (
    AdminConfirmRequest,
    AdminConfirmResponse,
    AdminSlotUpdateRequest,
)
from schemas.assignment import (
    AssignmentRecord,
    AssignmentCandidatesRequest,
    AssignmentCandidatesResponse,
    AssignmentCandidate,
    AssignmentGridResponse,
    AssignmentSheetsResponse,
    AutoAssignPeriodRequest,
    AutoAssignPeriodResponse,
    AutoAssignRequest,
    AutoAssignResponse,
    CancelAssignmentRequest,
    CancelAssignmentResponse,
    ImportAssignmentRequestsResponse,
    ManualAssignRequest,
    MatchRulesRequest,
    SlotCapacityUpdateRequest,
    PublishScheduleRequest,
    PublishScheduleRequestOnlyRequest,
    PublishScheduleRequestOnlyResponse,
    PublishScheduleResponse,
    PublishTeacherScheduleRequest,
    PublishTeacherScheduleRequestOnlyRequest,
    PublishTeacherScheduleRequestOnlyResponse,
    PublishTeacherScheduleResponse,
)
from schemas.change_request import (
    ChangeRequestItem,
    ChangeRequestListResponse,
    ChangeRequestResolveRequest,
    ChangeRequestResolveResponse,
    PublishAllRequest,
    PublishAllResponse,
)
from schemas.student_plan import (
    PeriodStudentPlansEntry,
    PeriodStudentPlansResponse,
    StudentSubjectPlansBody,
    StudentSubjectPlansResponse,
    SubjectPlanItem,
)
from schemas.entity import (
    StudentCreateRequest,
    StudentGroupedResponse,
    StudentGroup,
    StudentListResponse,
    StudentProfile,
    StudentUpdateRequest,
    TeacherCreateRequest,
    TeacherListResponse,
    TeacherProfile,
    TeacherUpdateRequest,
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
from services.assignment_grid import build_assignment_grid, manual_assign, update_slot_capacity
from services.assignment_sheets import build_assignment_sheets
from services.assignment_store import cancel_assignment_at_slot, get_assignments_between, get_assignments_for_date
from services.auto_assign import run_auto_assign
from services.availability_dashboard import build_availability_dashboard
from services.match_rules import MatchRules
from services.csv_import import import_assignment_requests_from_csv
from services.dashboard_builder import build_shift_dashboard, build_shift_dashboard_base_only
from services.data_loader import resolve_shift_date
from services.period_bootstrap import bootstrap_period_dashboards
from services.period_store import (
    create_period,
    delete_period,
    find_period_for_date,
    get_period,
    iter_dates,
    open_dates_for_period,
    list_deleted_periods,
    list_periods,
    restore_period,
    set_active_period,
    update_period_status,
)
from services.student_plan_store import get_preferred_teacher_id
from services.shift_excel import import_shift_excel_csv, import_shift_excel_xlsx, export_shift_excel_xlsx
from services.schedule_publish_store import (
    is_schedule_request_published,
    publish_all_schedules,
    publish_student_schedule_request,
    publish_student_schedule,
    publish_teacher_schedule,
    publish_teacher_schedule_request,
)
from services.change_request_store import count_pending_requests, list_change_requests, resolve_change_request
from services.shift_store import ensure_teacher_exists
from services.entity_store import get_student

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])
# 生徒・講師の自画面からも読む GET のみ、要ログイン止まりで公開する別ルーター。
shared_router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(get_current_user)])


@router.get("/dashboard/summary")
def get_dashboard_summary(period_id: int = Query(..., ge=1)) -> dict:
    """提案書送付・割当・未提出・変更申請の概要。"""
    from services.admin_dashboard import build_admin_dashboard_summary

    get_period(period_id)
    return build_admin_dashboard_summary(period_id)


@router.post("/backup")
def create_backup() -> dict:
    """DB と JSON データのスナップショットを backups/ に作成する。"""
    from scripts.backup_data import run_backup

    snapshot_dir, removed = run_backup()
    return {
        "snapshot": snapshot_dir.name,
        "removed": removed,
        "message": f"バックアップを作成しました（{snapshot_dir.name}）",
    }


@router.get("/schedule/full")
def get_schedule_full(period_id: int = Query(..., ge=1)) -> dict:
    """時間割正本（通常＋講習）。"""
    from services.class_schedule_store import get_full_schedule

    get_period(period_id)
    return get_full_schedule(period_id)


@router.get("/schedule/fixed")
def get_schedule_fixed_only(period_id: int = Query(..., ge=1)) -> dict:
    """通常授業（is_fixed=True）のみ。"""
    from services.class_schedule_store import get_fixed_only_schedule

    get_period(period_id)
    return get_fixed_only_schedule(period_id)


@router.get("/assignments/grid", response_model=AssignmentGridResponse)
def get_assignment_grid(date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$")) -> AssignmentGridResponse:
    """講師×コマの割当グリッド（1日分・後方互換）"""
    resolve_shift_date(date)
    return AssignmentGridResponse.model_validate(build_assignment_grid(date))


@router.get("/assignments/sheets", response_model=AssignmentSheetsResponse)
def get_assignment_sheets(period_id: int = Query(..., ge=1)) -> AssignmentSheetsResponse:
    """期間内の生徒・講師シート（日曜除外・複数日）"""
    get_period(period_id)
    return AssignmentSheetsResponse.model_validate(build_assignment_sheets(period_id))


@router.post("/assignments/manual", response_model=AssignmentGridResponse)
def assign_manual(body: ManualAssignRequest) -> AssignmentGridResponse:
    """手動で生徒を講師コマに割り当てる"""
    from services.entity_store import find_students_by_name, get_student

    resolve_shift_date(body.date)
    if body.student_id is not None:
        student = get_student(body.student_id)
        student_id = student["id"]
        student_name = student["name"]
    else:
        matches = find_students_by_name(body.student_name)
        if not matches:
            raise HTTPException(
                status_code=404,
                detail=f"生徒「{body.student_name}」が見つかりません。教室管理で登録してください",
            )
        if len(matches) > 1:
            raise HTTPException(
                status_code=400,
                detail=f"生徒「{body.student_name}」が同名で複数登録されています。教室管理で確認してください",
            )
        student_id = matches[0]["id"]
        student_name = matches[0]["name"]

    if not body.is_fixed and not body.subject.strip():
        raise HTTPException(status_code=400, detail="講習枠では科目を入力してください")

    rules = MatchRules.from_dict(body.rules.model_dump() if body.rules else None)
    all_assignments = None
    if body.period_id is not None:
        period = get_period(body.period_id)
        all_assignments = get_assignments_between(period.start_date, period.end_date)
    grid = manual_assign(
        body.date,
        student_id,
        student_name,
        body.subject,
        body.teacher_id,
        body.slot,
        rules=rules,
        all_assignments=all_assignments,
        skip_rules=body.skip_rules,
        is_fixed=body.is_fixed,
        period_id=body.period_id,
    )
    return AssignmentGridResponse.model_validate(grid)


@router.patch("/assignments/grid/capacity", response_model=AssignmentGridResponse)
def patch_grid_slot_capacity(body: SlotCapacityUpdateRequest) -> AssignmentGridResponse:
    """時間割セルの授業形態（1対2 / 1対4）を設定する"""
    resolve_shift_date(body.date)
    grid = update_slot_capacity(body.date, body.teacher_id, body.slot, body.max_lanes)
    return AssignmentGridResponse.model_validate(grid)


@router.post("/assignments/cancel", response_model=CancelAssignmentResponse)
def cancel_assignment(body: CancelAssignmentRequest) -> CancelAssignmentResponse:
    """割当を解除して未割当リクエストに戻す"""
    resolve_shift_date(body.date)
    get_period(body.period_id)
    cancelled = cancel_assignment_at_slot(
        body.date, body.teacher_id, body.slot, student_id=body.student_id
    )
    if cancelled is None:
        raise HTTPException(status_code=404, detail="割当が見つかりません")
    sheets = build_assignment_sheets(body.period_id)
    return CancelAssignmentResponse(
        message=f"{cancelled['student_name']} の {cancelled['subject']} 割当を解除しました",
        cancelled=AssignmentRecord.model_validate(cancelled),
        sheets=AssignmentSheetsResponse.model_validate(sheets),
    )


@router.post("/assignments/publish-schedule", response_model=PublishScheduleResponse)
def publish_schedule_to_student(body: PublishScheduleRequest) -> PublishScheduleResponse:
    """生徒の割当を確定し、生徒画面にスケジュールを送信する。"""
    period = get_period(body.period_id)
    if period.status == "DRAFT":
        raise HTTPException(status_code=409, detail="DRAFT 期間では確定送信できません")
    if not is_schedule_request_published(body.period_id, body.student_id):
        raise HTTPException(
            status_code=409,
            detail="提案書が未送付です。先に「提案書を送付（回答依頼）」を行ってください",
        )
    student = get_student(body.student_id)
    sheets = build_assignment_sheets(body.period_id)
    student_row = next((s for s in sheets["students"] if s["id"] == body.student_id), None)
    pending = student_row["pending_count"] if student_row else 0
    if pending > 0:
        raise HTTPException(
            status_code=409,
            detail=f"未割当が {pending} 件残っているため確定できません",
        )
    already = not publish_student_schedule(body.period_id, body.student_id)
    sheets = build_assignment_sheets(body.period_id)
    if already:
        msg = f"「{student['name']}」は既に確定済みです"
    else:
        msg = f"「{student['name']}」にスケジュールを送信しました。生徒画面で確認できます。"
    return PublishScheduleResponse(
        message=msg,
        already_published=already,
        sheets=AssignmentSheetsResponse.model_validate(sheets),
    )


@router.post("/assignments/publish-request", response_model=PublishScheduleRequestOnlyResponse)
def publish_request_to_student(body: PublishScheduleRequestOnlyRequest) -> PublishScheduleRequestOnlyResponse:
    """生徒に初回提案書（回答依頼）を送付する。"""
    period = get_period(body.period_id)
    if period.status == "DRAFT":
        period = update_period_status(body.period_id, "COLLECTING")
    if period.status != "COLLECTING":
        raise HTTPException(status_code=409, detail="初回提案書の送付は COLLECTING 期間のみ可能です")
    student = get_student(body.student_id)
    already = not publish_student_schedule_request(body.period_id, body.student_id)
    sheets = build_assignment_sheets(body.period_id)
    if already:
        msg = f"「{student['name']}」には既に提案書を送付済みです"
    else:
        msg = f"「{student['name']}」に提案書を送付しました。生徒画面で回答できます。"
    return PublishScheduleRequestOnlyResponse(
        message=msg,
        already_published=already,
        sheets=AssignmentSheetsResponse.model_validate(sheets),
    )


@router.post("/assignments/publish-teacher-request", response_model=PublishTeacherScheduleRequestOnlyResponse)
def publish_request_to_teacher(
    body: PublishTeacherScheduleRequestOnlyRequest,
) -> PublishTeacherScheduleRequestOnlyResponse:
    """講師に初回提案書（回答依頼）を送付する。"""
    period = get_period(body.period_id)
    if period.status == "DRAFT":
        period = update_period_status(body.period_id, "COLLECTING")
    if period.status != "COLLECTING":
        raise HTTPException(status_code=409, detail="初回提案書の送付は COLLECTING 期間のみ可能です")
    sheets = build_assignment_sheets(body.period_id)
    teacher_row = next((t for t in sheets["teachers"] if t["id"] == body.teacher_id), None)
    if teacher_row is None:
        raise HTTPException(status_code=404, detail="講師が見つかりません")
    already = not publish_teacher_schedule_request(body.period_id, body.teacher_id)
    sheets = build_assignment_sheets(body.period_id)
    if already:
        msg = f"「{teacher_row['name']}」には既に提案書を送付済みです"
    else:
        msg = f"「{teacher_row['name']}」に提案書を送付しました。講師画面で回答できます。"
    return PublishTeacherScheduleRequestOnlyResponse(
        message=msg,
        already_published=already,
        sheets=AssignmentSheetsResponse.model_validate(sheets),
    )


@router.post("/assignments/publish-teacher-schedule", response_model=PublishTeacherScheduleResponse)
def publish_schedule_to_teacher(body: PublishTeacherScheduleRequest) -> PublishTeacherScheduleResponse:
    """講師に確定スケジュールを送付する。"""
    get_period(body.period_id)
    sheets = build_assignment_sheets(body.period_id)
    teacher_row = next((t for t in sheets["teachers"] if t["id"] == body.teacher_id), None)
    if teacher_row is None:
        raise HTTPException(status_code=404, detail="講師が見つかりません")
    if not teacher_row.get("schedule_requested"):
        raise HTTPException(
            status_code=409,
            detail="提案書を送付してから確定してください",
        )
    already = not publish_teacher_schedule(body.period_id, body.teacher_id)
    sheets = build_assignment_sheets(body.period_id)
    if already:
        msg = f"「{teacher_row['name']}」は既に送付済みです"
    else:
        msg = f"「{teacher_row['name']}」にスケジュールを送信しました。講師画面で確認できます。"
    return PublishTeacherScheduleResponse(
        message=msg,
        already_published=already,
        sheets=AssignmentSheetsResponse.model_validate(sheets),
    )


@router.post("/assignments/publish-all", response_model=PublishAllResponse)
def publish_all_schedules_to_members(body: PublishAllRequest) -> PublishAllResponse:
    """割当済み生徒・全講師にスケジュールを一括送付。"""
    get_period(body.period_id)
    result = publish_all_schedules(body.period_id)
    skipped = result["students_skipped"]
    msg = (
        f"生徒 {result['students_published']} 名・講師 {result['teachers_published']} 名に送付しました"
    )
    if skipped:
        msg += f"（未割当のためスキップ: {', '.join(skipped)}）"
    return PublishAllResponse(
        period_id=body.period_id,
        students_published=result["students_published"],
        students_skipped=skipped,
        teachers_published=result["teachers_published"],
        message=msg,
    )


@shared_router.get("/change-requests", response_model=ChangeRequestListResponse)
def get_change_requests(
    period_id: int = Query(..., ge=1),
    status: str | None = Query(None, pattern="^(PENDING|APPROVED|REJECTED)$"),
) -> ChangeRequestListResponse:
    requests = list_change_requests(period_id, status=status)
    pending = count_pending_requests(period_id)
    return ChangeRequestListResponse(
        period_id=period_id,
        requests=[ChangeRequestItem.model_validate(r) for r in requests],
        pending_count=pending,
    )


@router.patch("/change-requests/{request_id}", response_model=ChangeRequestResolveResponse)
def resolve_change_request_endpoint(
    request_id: int,
    body: ChangeRequestResolveRequest,
) -> ChangeRequestResolveResponse:
    row = resolve_change_request(request_id, body.action)
    action_label = "承認" if body.action == "approve" else "却下"
    if body.action == "approve" and row.get("request_type") == "RESUBMIT":
        if row.get("role") == "student":
            detail = "割当を白紙に戻し、再提出を依頼しました"
        else:
            detail = "提出をリセットし、再提出を依頼しました"
        msg = f"変更申請を承認しました（{detail}）"
    else:
        msg = f"変更申請を{action_label}しました"
    return ChangeRequestResolveResponse(
        request=ChangeRequestItem.model_validate(row),
        message=msg,
    )


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
    period = find_period_for_date(body.date)
    preferred = (
        get_preferred_teacher_id(period.id, body.student_id, body.subject)
        if period is not None
        else None
    )

    raw = get_assignment_candidates(
        student_id=body.student_id,
        subject=body.subject,
        teacher_list=teacher_list,
        current_assignments=current_assignments,
        date=body.date,
        preferred_teacher_id=preferred,
    )
    from services.assignment_engine import load_student_slots

    student_slots = load_student_slots(body.student_id, body.date)
    ranked = rank_candidates(
        raw,
        teacher_list,
        body.date,
        current_assignments,
        student_slots=student_slots,
        subject=body.subject,
    )
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


@router.post("/auto-assign-period", response_model=AutoAssignPeriodResponse)
def auto_assign_period(body: AutoAssignPeriodRequest) -> AutoAssignPeriodResponse:
    period = get_period(body.period_id)
    rules = MatchRules.from_dict(body.rules.model_dump() if body.rules else None)
    open_dates = open_dates_for_period(period)
    all_assignments = get_assignments_between(period.start_date, period.end_date)
    total = 0
    for iso_date in open_dates:
        proposals, _, _ = run_auto_assign(iso_date, rules=rules, all_assignments=all_assignments)
        total += len(proposals)
    sheets = build_assignment_sheets(body.period_id)
    return AutoAssignPeriodResponse(
        period_id=body.period_id,
        message=f"期間内 {total} 件の自動割当を実行しました",
        assigned_count=total,
        sheets=AssignmentSheetsResponse.model_validate(sheets),
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


@router.get("/periods/deleted", response_model=PeriodListResponse)
def get_deleted_periods() -> PeriodListResponse:
    _, active_id = list_periods()
    return PeriodListResponse(periods=list_deleted_periods(), active_period_id=active_id)


@router.get("/periods/{period_id}/student-plans", response_model=PeriodStudentPlansResponse)
def get_period_student_plans(period_id: int) -> PeriodStudentPlansResponse:
    from services.entity_store import list_students
    from services.period_store import get_period
    from services.student_plan_store import list_plans_for_period

    period = get_period(period_id)
    plans_by_student = list_plans_for_period(period_id)
    entries: list[PeriodStudentPlansEntry] = []
    for student in list_students():
        sid = student["id"]
        plans = [SubjectPlanItem.model_validate(p) for p in plans_by_student.get(sid, [])]
        entries.append(
            PeriodStudentPlansEntry(
                student_id=sid,
                student_name=student["name"],
                grade_label=student.get("grade_label", ""),
                plans=plans,
            )
        )
    return PeriodStudentPlansResponse(
        period_id=period_id,
        period_name=period.name,
        students=entries,
    )


@router.get(
    "/periods/{period_id}/students/{student_id}/plans",
    response_model=StudentSubjectPlansResponse,
)
def get_student_subject_plans(period_id: int, student_id: int) -> StudentSubjectPlansResponse:
    from services.entity_store import get_student
    from services.student_plan_store import list_plans_for_student

    student = get_student(student_id)
    plans = [SubjectPlanItem.model_validate(p) for p in list_plans_for_student(period_id, student_id)]
    return StudentSubjectPlansResponse(
        period_id=period_id,
        student_id=student_id,
        student_name=student["name"],
        plans=plans,
        synced_request_count=0,
    )


@router.put(
    "/periods/{period_id}/students/{student_id}/plans",
    response_model=StudentSubjectPlansResponse,
)
def save_student_subject_plans(
    period_id: int,
    student_id: int,
    body: StudentSubjectPlansBody,
) -> StudentSubjectPlansResponse:
    from services.entity_store import get_student
    from services.student_plan_store import save_student_plans

    student = get_student(student_id)
    saved, synced = save_student_plans(
        period_id,
        student_id,
        [p.model_dump() for p in body.plans],
    )
    return StudentSubjectPlansResponse(
        period_id=period_id,
        student_id=student_id,
        student_name=student["name"],
        plans=[SubjectPlanItem.model_validate(p) for p in saved],
        synced_request_count=synced,
    )


@router.get("/students", response_model=StudentListResponse)
def get_students() -> StudentListResponse:
    from services.entity_store import list_students

    return StudentListResponse(students=[StudentProfile.model_validate(s) for s in list_students()])


@router.get("/students/grouped", response_model=StudentGroupedResponse)
def get_students_grouped() -> StudentGroupedResponse:
    from services.entity_store import list_students_grouped

    groups = [StudentGroup.model_validate(g) for g in list_students_grouped()]
    return StudentGroupedResponse(groups=groups)


@router.post("/students", response_model=StudentProfile)
def add_student(body: StudentCreateRequest) -> StudentProfile:
    from services.entity_store import create_student

    return StudentProfile.model_validate(create_student(body.name, body.school_level, body.grade_year))


@router.patch("/students/{student_id}", response_model=StudentProfile)
def edit_student(student_id: int, body: StudentUpdateRequest) -> StudentProfile:
    from services.entity_store import update_student

    return StudentProfile.model_validate(
        update_student(student_id, body.name, body.school_level, body.grade_year)
    )


@router.delete("/students/{student_id}")
def remove_student(student_id: int) -> dict:
    from services.entity_store import delete_student

    delete_student(student_id)
    return {"message": "生徒を削除しました"}


@router.post("/students/{student_id}/reset-password", response_model=StudentProfile)
def reset_student_password_endpoint(student_id: int) -> StudentProfile:
    from services.entity_store import reset_student_password

    return StudentProfile.model_validate(reset_student_password(student_id))


@router.get("/teachers", response_model=TeacherListResponse)
def get_teachers_master() -> TeacherListResponse:
    from services.entity_store import list_teachers

    return TeacherListResponse(teachers=[TeacherProfile.model_validate(t) for t in list_teachers()])


@router.post("/teachers", response_model=TeacherProfile)
def add_teacher(body: TeacherCreateRequest) -> TeacherProfile:
    from services.entity_store import create_teacher

    return TeacherProfile.model_validate(create_teacher(body.name, body.color))


@router.patch("/teachers/{teacher_id}", response_model=TeacherProfile)
def edit_teacher(teacher_id: int, body: TeacherUpdateRequest) -> TeacherProfile:
    from services.entity_store import update_teacher

    return TeacherProfile.model_validate(update_teacher(teacher_id, body.name, body.color))


@router.delete("/teachers/{teacher_id}")
def remove_teacher(teacher_id: int) -> dict:
    from services.entity_store import delete_teacher

    delete_teacher(teacher_id)
    return {"message": "講師を削除しました"}


@router.post("/teachers/{teacher_id}/reset-password", response_model=TeacherProfile)
def reset_teacher_password_endpoint(teacher_id: int) -> TeacherProfile:
    from services.entity_store import reset_teacher_password

    return TeacherProfile.model_validate(reset_teacher_password(teacher_id))


@router.post("/periods", response_model=PeriodResponse)
def create_shift_period(body: PeriodCreateRequest) -> PeriodResponse:
    period = create_period(
        body.name,
        body.start_date,
        body.end_date,
        body.closed_dates,
        location_slug=body.location_slug,
        submission_deadline=body.submission_deadline,
    )
    open_dates = open_dates_for_period(period)
    day_count = bootstrap_period_dashboards(period.id)
    closed_note = f"・休校 {len(body.closed_dates)} 日" if body.closed_dates else ""
    return PeriodResponse(
        period=period,
        dates=iter_dates(period.start_date, period.end_date),
        open_dates=open_dates,
        message=f"講習「{period.name}」を作成しました（開校 {day_count} 日分{closed_note}）",
    )


@router.patch("/periods/{period_id}/activate", response_model=PeriodResponse)
def activate_period(period_id: int) -> PeriodResponse:
    period = set_active_period(period_id)
    open_dates = open_dates_for_period(period)
    return PeriodResponse(
        period=period,
        dates=iter_dates(period.start_date, period.end_date),
        open_dates=open_dates,
        message=f"講習「{period.name}」を選択しました",
    )


@router.delete("/periods/{period_id}", response_model=PeriodResponse)
def remove_period(period_id: int) -> PeriodResponse:
    period = delete_period(period_id)
    return PeriodResponse(
        period=period,
        dates=iter_dates(period.start_date, period.end_date),
        open_dates=[],
        message=f"講習「{period.name}」を削除しました（復元可能）",
    )


@router.patch("/periods/{period_id}/restore", response_model=PeriodResponse)
def restore_deleted_period(period_id: int) -> PeriodResponse:
    period = restore_period(period_id)
    open_dates = open_dates_for_period(period)
    return PeriodResponse(
        period=period,
        dates=iter_dates(period.start_date, period.end_date),
        open_dates=open_dates,
        message=f"講習「{period.name}」を復元しました",
    )


@router.patch("/periods/{period_id}/status", response_model=PeriodResponse)
def change_period_status(period_id: int, body: PeriodStatusUpdateRequest) -> PeriodResponse:
    if body.status == "FINALIZED":
        sheets = build_assignment_sheets(period_id)
        pending_total = sheets.get("pending_total", 0)
        if pending_total > 0 and not body.force:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"未割当が {pending_total} 件残っています。"
                    "割当を完了するか、force: true で強制確定してください。"
                ),
            )
    period = update_period_status(period_id, body.status)
    open_dates = open_dates_for_period(period)
    msg = f"期間ステータスを {body.status} に更新しました"
    if body.status == "FINALIZED":
        publish_result = publish_all_schedules(period_id)
        msg = (
            f"シフトを確定しました。"
            f" 生徒 {publish_result['students_published']} 名・"
            f"講師 {publish_result['teachers_published']} 名にスケジュールを送付しました。"
        )
        if publish_result["students_skipped"]:
            msg += f"（未割当スキップ: {', '.join(publish_result['students_skipped'])}）"
    return PeriodResponse(
        period=period,
        dates=iter_dates(period.start_date, period.end_date),
        open_dates=open_dates,
        message=msg,
    )


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
