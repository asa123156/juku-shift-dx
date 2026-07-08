from pydantic import BaseModel, Field

from services.slot_timing import SLOT_COUNT


class AssignmentRecord(BaseModel):
    date: str
    student_id: int
    student_name: str
    subject: str = Field(default="")
    teacher_id: int
    teacher_name: str
    slot: int = Field(ge=1, le=SLOT_COUNT)
    lesson_kind: str = Field(default="講習", pattern="^(通常|講習)$")
    is_fixed: bool | None = Field(default=None, description="True=通常授業（◎固定）")


class AssignmentCandidate(BaseModel):
    teacher_id: int
    teacher_name: str
    slot: int = Field(ge=1, le=SLOT_COUNT)
    match_score: int = Field(ge=0, le=100, description="マッチ度（高いほど適合）")


class AssignmentCandidatesRequest(BaseModel):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    student_id: int = Field(ge=1)
    subject: str = Field(min_length=1)


class AssignmentCandidatesResponse(BaseModel):
    date: str
    student_id: int
    subject: str
    candidates: list[AssignmentCandidate]


class AutoAssignRequest(BaseModel):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class AutoAssignProposal(BaseModel):
    student_id: int
    student_name: str
    subject: str
    teacher_id: int
    teacher_name: str
    slot: int
    match_score: int


class AssignmentRequestItem(BaseModel):
    student_id: int = Field(ge=1)
    student_name: str = Field(min_length=1)
    subject: str = Field(min_length=1)


class ImportAssignmentRequestsResponse(BaseModel):
    imported_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    by_date: dict[str, int] = Field(description="日付ごとの追加件数")
    message: str


class MatchRulesRequest(BaseModel):
    no_teacher_gaps: bool = True
    weekly_limits: dict[str, int] = Field(
        default_factory=lambda: {"国語": 1, "数学": 2, "英語": 0, "理科": 0, "社会": 0}
    )


class ManualAssignRequest(BaseModel):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    student_id: int | None = Field(default=None, ge=1)
    student_name: str = Field(min_length=1)
    subject: str = Field(default="", description="講習枠では必須。通常（is_fixed）では省略可")
    teacher_id: int = Field(ge=1)
    slot: int = Field(ge=1, le=SLOT_COUNT)
    period_id: int | None = Field(default=None, ge=1)
    is_fixed: bool = Field(default=False, description="True=通常授業（◎固定）")
    rules: MatchRulesRequest | None = None
    skip_rules: bool = Field(
        default=False,
        description="時間割表からの直接入力時は True（シフト希望・週上限などをスキップ）",
    )


class AssignmentGridSlot(BaseModel):
    slot: int
    availability: str
    assignable: bool
    max_lanes: int = Field(default=2, ge=2, le=4)
    lesson_format: str = Field(default="1対2")
    assignments: list[AssignmentRecord] = Field(default_factory=list)
    assignment: AssignmentRecord | None = None
    lanes: list[dict] = Field(default_factory=list)


class SlotCapacityUpdateRequest(BaseModel):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    teacher_id: int = Field(ge=1)
    slot: int = Field(ge=1, le=SLOT_COUNT)
    max_lanes: int = Field(ge=2, le=4, description="2=1対2, 4=1対4")


class StudentSubjectPlanItem(BaseModel):
    subject: str
    slot_count: int = Field(ge=0)
    teacher_id: int | None = None
    teacher_name: str | None = None


class AssignmentGridTeacher(BaseModel):
    id: int
    name: str
    color: str = ""
    slots: list[AssignmentGridSlot]


class AssignmentGridStudentSlot(BaseModel):
    slot: int
    availability: str
    assignment: AssignmentRecord | None = None


class AssignmentGridStudent(BaseModel):
    id: int
    name: str
    slots: list[AssignmentGridStudentSlot]
    pending_subjects: list[str] = Field(default_factory=list)


class AssignmentGridResponse(BaseModel):
    date: str
    time_slots: list
    teachers: list[AssignmentGridTeacher]
    students: list[AssignmentGridStudent] = Field(default_factory=list)
    assignments: list[AssignmentRecord]
    pending_requests: list[AssignmentRequestItem]


class AutoAssignResponse(BaseModel):
    date: str
    message: str
    proposals: list[AutoAssignProposal]
    assignments: list[AssignmentRecord]
    grid: AssignmentGridResponse


class AssignmentDateLabel(BaseModel):
    date: str
    label: str
    weekday: str


class AssignmentSheetStudentDay(BaseModel):
    slots: list[AssignmentGridStudentSlot]
    pending_subjects: list[str] = Field(default_factory=list)


class AssignmentSheetStudent(BaseModel):
    id: int
    name: str
    school_level: str = ""
    grade_year: int = 0
    grade_label: str = ""
    level_label: str = ""
    days: dict[str, AssignmentSheetStudentDay]
    pending_count: int = 0
    assigned_count: int = 0
    subjects: list[str] = Field(default_factory=list)
    subject_plans: list[StudentSubjectPlanItem] = Field(default_factory=list)
    schedule_requested: bool = False
    schedule_published: bool = False


class PublishScheduleRequestOnlyRequest(BaseModel):
    period_id: int = Field(ge=1)
    student_id: int = Field(ge=1)


class PublishScheduleRequest(BaseModel):
    period_id: int = Field(ge=1)
    student_id: int = Field(ge=1)


class AssignmentSheetTeacherDay(BaseModel):
    slots: list[AssignmentGridSlot]


class AssignmentSheetTeacher(BaseModel):
    id: int
    name: str
    color: str = ""
    days: dict[str, AssignmentSheetTeacherDay]
    schedule_requested: bool = False
    schedule_published: bool = False


class PublishTeacherScheduleRequestOnlyRequest(BaseModel):
    period_id: int = Field(ge=1)
    teacher_id: int = Field(ge=1)


class AssignmentSheetsResponse(BaseModel):
    period_id: int
    period_name: str
    period_status: str
    dates: list[AssignmentDateLabel]
    time_slots: list
    students: list[AssignmentSheetStudent]
    teachers: list[AssignmentSheetTeacher]
    pending_by_date: dict[str, list[AssignmentRequestItem]]
    pending_total: int = 0


class PublishScheduleRequestOnlyResponse(BaseModel):
    message: str
    already_published: bool = False
    sheets: AssignmentSheetsResponse


class PublishTeacherScheduleRequestOnlyResponse(BaseModel):
    message: str
    already_published: bool = False
    sheets: AssignmentSheetsResponse


class PublishScheduleResponse(BaseModel):
    message: str
    already_published: bool = False
    sheets: AssignmentSheetsResponse


class PublishTeacherScheduleRequest(BaseModel):
    period_id: int = Field(ge=1)
    teacher_id: int = Field(ge=1)


class PublishTeacherScheduleResponse(BaseModel):
    message: str
    already_published: bool = False
    sheets: AssignmentSheetsResponse


class AutoAssignPeriodRequest(BaseModel):
    period_id: int = Field(ge=1)
    rules: MatchRulesRequest | None = None


class AutoAssignPeriodResponse(BaseModel):
    period_id: int
    message: str
    assigned_count: int
    sheets: AssignmentSheetsResponse


class CancelAssignmentRequest(BaseModel):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    teacher_id: int = Field(ge=1)
    slot: int = Field(ge=1, le=SLOT_COUNT)
    period_id: int = Field(ge=1)
    student_id: int | None = Field(default=None, ge=1)


class CancelAssignmentResponse(BaseModel):
    message: str
    cancelled: AssignmentRecord | None = None
    sheets: AssignmentSheetsResponse
