from typing import Literal

from pydantic import BaseModel, Field, field_validator

PeriodStatus = Literal["DRAFT", "COLLECTING", "FINALIZED"]
SlotSymbol = Literal["◎", "×", ""]
SubmitRole = Literal["teacher", "student"]

SLOT_KEYS = frozenset({"1", "2", "3", "4"})


def empty_slots() -> dict[str, SlotSymbol]:
    return {"1": "", "2": "", "3": "", "4": ""}


class Period(BaseModel):
    id: int
    name: str = Field(min_length=1)
    start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: PeriodStatus = "DRAFT"


class PeriodCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, end_date: str, info) -> str:
        start = info.data.get("start_date")
        if start and end_date < start:
            raise ValueError("end_date must be on or after start_date")
        return end_date


class PeriodStatusUpdateRequest(BaseModel):
    status: PeriodStatus


class PeriodResponse(BaseModel):
    period: Period
    dates: list[str]
    message: str


class PeriodListResponse(BaseModel):
    periods: list[Period]
    active_period_id: int | None = None


class DaySubmission(BaseModel):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    slots: dict[str, SlotSymbol]

    @field_validator("slots")
    @classmethod
    def validate_slots(cls, slots: dict[str, SlotSymbol]) -> dict[str, SlotSymbol]:
        if set(slots.keys()) != SLOT_KEYS:
            raise ValueError('slots must include exactly "1", "2", "3", and "4"')
        return slots


class BulkShiftSubmitRequest(BaseModel):
    role: SubmitRole
    entity_id: int = Field(ge=1, description="teacher_id または student_id")
    period_id: int = Field(ge=1)
    submissions: list[DaySubmission] = Field(min_length=1)


class BulkShiftSubmitResponse(BaseModel):
    role: SubmitRole
    entity_id: int
    period_id: int
    saved_dates: list[str]
    message: str


class ScheduleDay(BaseModel):
    date: str
    slots: dict[str, SlotSymbol]
    locked_slots: dict[str, bool] = Field(description="◎ 固定枠は true")
    readonly: bool = False
    confirmed_lessons: list[dict] = Field(default_factory=list, description="確定後の割当（生徒向け）")


class MyScheduleResponse(BaseModel):
    role: SubmitRole
    entity_id: int
    period_id: int
    period_name: str
    period_status: PeriodStatus
    readonly: bool
    time_slots: list[dict] = Field(default_factory=list)
    message: str | None = None
    dates: list[ScheduleDay]


class ShiftImportResponse(BaseModel):
    period_id: int
    imported_count: int
    message: str
