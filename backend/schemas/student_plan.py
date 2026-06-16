from pydantic import BaseModel, Field


class SubjectPlanItem(BaseModel):
    subject: str = Field(min_length=1, description="教科名")
    slot_count: int = Field(ge=0, le=60, description="講習期間中の希望コマ数")


class StudentSubjectPlansBody(BaseModel):
    plans: list[SubjectPlanItem] = Field(default_factory=list)


class StudentSubjectPlansResponse(BaseModel):
    period_id: int
    student_id: int
    student_name: str
    plans: list[SubjectPlanItem]
    synced_request_count: int = 0


class PeriodStudentPlansEntry(BaseModel):
    student_id: int
    student_name: str
    grade_label: str = ""
    plans: list[SubjectPlanItem]


class PeriodStudentPlansResponse(BaseModel):
    period_id: int
    period_name: str
    students: list[PeriodStudentPlansEntry]
