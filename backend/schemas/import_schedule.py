from pydantic import BaseModel, Field


class ScheduleCsvImportResponse(BaseModel):
    period_id: int
    rows_processed: int = Field(description="取り込んだデータ行数")
    teachers_created: int = Field(description="新規登録した講師数")
    students_created: int = Field(description="新規登録した生徒数")
    teacher_slots_saved: int = Field(description="講師固定枠の登録数")
    student_slots_saved: int = Field(description="生徒固定枠の登録数")
    blank_slots: int = Field(description="調整用枠（空白）として登録したコマ数")
    regular_slots: int = Field(description="通常授業（◎）として登録したコマ数")
    message: str


class JukuGridImportResponse(BaseModel):
    period_id: int
    resolved_date: str | None = None
    resolved_dates: list[str] = Field(default_factory=list)
    sheet_name: str | None = None
    imported_sheet_count: int = 0
    imported_sheets: list[str] = Field(default_factory=list)
    workbook_filename: str | None = None
    parsed_rows: int = Field(description="グリッドから抽出した行数")
    rows_processed: int
    teachers_created: int
    students_created: int
    teacher_slots_saved: int
    student_slots_saved: int
    blank_slots: int
    regular_slots: int
    requests_added: int
    requests_skipped: int
    dashboard_teachers_added: int = 0
    message: str
