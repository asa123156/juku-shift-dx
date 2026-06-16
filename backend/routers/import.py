from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from schemas.import_schedule import JukuGridImportResponse, ScheduleCsvImportResponse
from services.juku_grid_import import import_juku_grid_workbook, import_juku_grid_xlsx
from services.schedule_csv_import import import_schedule_csv

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/schedule", response_model=ScheduleCsvImportResponse)
async def import_schedule_from_csv(
    period_id: int = Query(..., ge=1, description="取り込み先の講習期間 ID"),
    file: UploadFile = File(
        ...,
        description="講師名, 氏名, 学年, 科目, 種別, 日付, コマ 形式の CSV",
    ),
) -> ScheduleCsvImportResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV ファイルを指定してください")

    raw = await file.read()
    content: str | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            content = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if content is None:
        raise HTTPException(status_code=400, detail="CSV の文字コードを判別できません")

    stats = import_schedule_csv(period_id, content)
    regular = stats["regular_slots"]
    blank = stats["blank_slots"]
    return ScheduleCsvImportResponse(
        period_id=period_id,
        rows_processed=stats["rows_processed"],
        teachers_created=stats["teachers_created"],
        students_created=stats["students_created"],
        teacher_slots_saved=stats["teacher_slots_saved"],
        student_slots_saved=stats["student_slots_saved"],
        blank_slots=blank,
        regular_slots=regular,
        message=(
            f"{stats['rows_processed']} 行を取り込みました"
            f"（通常授業 ◎ {regular} コマ / 調整用空白 {blank} コマ"
            f" / 講師新規 {stats['teachers_created']} 名 / 生徒新規 {stats['students_created']} 名）"
        ),
    )


@router.post("/juku-grid", response_model=JukuGridImportResponse)
async def import_juku_grid_schedule(
    period_id: int = Query(..., ge=1, description="取り込み先の講習期間 ID"),
    date: str | None = Query(None, description="単日取込時の対象日 YYYY-MM-DD"),
    sheet_name: str | None = Query(None, description="単日取込時のシート名"),
    file: UploadFile = File(..., description="月次時間割 Excel（白庭台形式）"),
) -> JukuGridImportResponse:
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Excel (.xlsx) ファイルを指定してください")

    raw = await file.read()
    filename = file.filename or "schedule.xlsx"

    if date:
        stats = import_juku_grid_xlsx(period_id, raw, date, sheet_name, filename=filename)
        message = (
            f"{stats['rows_processed']} 件を取り込みました"
            f"（{stats['resolved_date']} / 抽出 {stats['parsed_rows']} 行"
            f" / リクエスト +{stats['requests_added']} 重複 {stats['requests_skipped']}"
            f" / ダッシュボード講師 +{stats.get('dashboard_teachers_added', 0)}）"
        )
    else:
        stats = import_juku_grid_workbook(period_id, raw, filename)
        sheets = stats.get("imported_sheets") or []
        message = (
            f"{stats['imported_sheet_count']} シート・{stats['rows_processed']} 件を取り込みました"
            f"（{', '.join(sheets[:5])}{'…' if len(sheets) > 5 else ''}"
            f" / リクエスト +{stats['requests_added']} 重複 {stats['requests_skipped']}）"
        )

    return JukuGridImportResponse(
        period_id=period_id,
        resolved_date=stats.get("resolved_date"),
        resolved_dates=stats.get("resolved_dates") or [],
        sheet_name=stats.get("sheet_name") or sheet_name,
        imported_sheet_count=stats.get("imported_sheet_count", 1),
        imported_sheets=stats.get("imported_sheets") or [],
        workbook_filename=stats.get("workbook_filename") or filename,
        parsed_rows=stats["parsed_rows"],
        rows_processed=stats["rows_processed"],
        teachers_created=stats["teachers_created"],
        students_created=stats["students_created"],
        teacher_slots_saved=stats["teacher_slots_saved"],
        student_slots_saved=stats["student_slots_saved"],
        blank_slots=stats["blank_slots"],
        regular_slots=stats["regular_slots"],
        requests_added=stats["requests_added"],
        requests_skipped=stats["requests_skipped"],
        dashboard_teachers_added=stats.get("dashboard_teachers_added", 0),
        message=message,
    )
