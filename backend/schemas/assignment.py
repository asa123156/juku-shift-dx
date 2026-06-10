from pydantic import BaseModel, Field

from schemas.shifts import ShiftDashboardResponse


class AssignmentRecord(BaseModel):
    date: str
    student_id: int
    student_name: str
    subject: str
    teacher_id: int
    teacher_name: str
    slot: int = Field(ge=1, le=4)


class AssignmentCandidate(BaseModel):
    teacher_id: int
    teacher_name: str
    slot: int = Field(ge=1, le=4)
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


class AutoAssignResponse(BaseModel):
    date: str
    message: str
    proposals: list[AutoAssignProposal]
    assignments: list[AssignmentRecord]
    dashboard: ShiftDashboardResponse


class AssignmentRequestItem(BaseModel):
    student_id: int = Field(ge=1)
    student_name: str = Field(min_length=1)
    subject: str = Field(min_length=1)


class ImportAssignmentRequestsResponse(BaseModel):
    imported_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    by_date: dict[str, int] = Field(description="日付ごとの追加件数")
    message: str
