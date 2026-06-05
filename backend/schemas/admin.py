from pydantic import BaseModel, Field

from schemas.shifts import ShiftDashboardResponse, ShiftStatus


class AdminSlotUpdateRequest(BaseModel):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    teacher_id: int = Field(ge=1)
    slot: int = Field(ge=1, le=4)
    status: ShiftStatus


class AdminConfirmRequest(BaseModel):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class AdminConfirmResponse(BaseModel):
    date: str
    confirmed_slots: int
    message: str
    dashboard: ShiftDashboardResponse


class ShiftDatesResponse(BaseModel):
    dates: list[str]
    default_date: str


class TeacherListItem(BaseModel):
    id: int
    name: str
    color: str
