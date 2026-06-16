from pydantic import BaseModel, Field


class GoogleStatusResponse(BaseModel):
    configured: bool
    message: str


class GoogleSheetImportRequest(BaseModel):
    period_id: int = Field(..., ge=1)
    spreadsheet_ref: str = Field(..., description="スプレッドシート URL または ID")
    date: str | None = Field(None, description="単日取込時 YYYY-MM-DD（省略時は全日次シート）")
    sheet_name: str | None = Field(None, description="単日取込時のシート名（任意）")


class GoogleSheetImportResponse(BaseModel):
    period_id: int
    spreadsheet_id: str = ""
    resolved_date: str | None = None
    sheet_name: str | None = None
    parsed_rows: int = 0
    rows_processed: int = 0
    teachers_created: int = 0
    students_created: int = 0
    teacher_slots_saved: int = 0
    student_slots_saved: int = 0
    blank_slots: int = 0
    regular_slots: int = 0
    requests_added: int = 0
    requests_skipped: int = 0
    dashboard_teachers_added: int = 0
    imported_sheet_count: int | None = None
    dates: list[str] | None = None
    sheets: list[str] | None = None
    skipped_sheets: list[str] | None = None
    message: str


class GoogleSheetExportRequest(BaseModel):
    period_id: int = Field(..., ge=1)
    spreadsheet_ref: str | None = Field(None, description="既存スプレッドシート URL/ID（省略時は新規作成）")
    title: str | None = Field(None, description="新規作成時のファイル名")


class GoogleSheetExportResponse(BaseModel):
    spreadsheet_id: str
    web_view_link: str
    message: str
