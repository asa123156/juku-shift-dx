from typing import Literal

from pydantic import BaseModel, Field, field_validator

from services.slot_timing import SLOT_KEYS as _SLOT_KEY_LIST, empty_slot_map

PeriodStatus = Literal["DRAFT", "COLLECTING", "FINALIZED"]
PeriodKind = Literal["REGULAR", "CRAM"]
SlotSymbol = Literal["◎", "×", ""]
SubmitRole = Literal["teacher", "student"]

SLOT_KEYS = frozenset(_SLOT_KEY_LIST)


def empty_slots() -> dict[str, SlotSymbol]:
    return empty_slot_map()  # type: ignore[return-value]


class Period(BaseModel):
    id: int
    name: str = Field(min_length=1)
    start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: PeriodStatus = "DRAFT"
    closed_dates: list[str] = Field(default_factory=list, description="休校日（日曜以外で除外する日）")
    is_deleted: bool = False
    location_slug: str = Field(default="hakutei", description="時間割出力形式（拠点フォルダ slug）")
    period_kind: PeriodKind = Field(default="CRAM", description="REGULAR=年度通常授業, CRAM=講習")


class PeriodCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    closed_dates: list[str] = Field(default_factory=list, description="開校しない日（日曜は自動除外）")
    location_slug: str = Field(default="hakutei", min_length=1, description="時間割出力形式（拠点 slug）")

    @field_validator("closed_dates")
    @classmethod
    def validate_closed_dates(cls, dates: list[str]) -> list[str]:
        return sorted(set(dates))

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, end_date: str, info) -> str:
        start = info.data.get("start_date")
        if start and end_date < start:
            raise ValueError("end_date must be on or after start_date")
        return end_date


class PeriodStatusUpdateRequest(BaseModel):
    status: PeriodStatus
    force: bool = Field(default=False, description="未割当が残っていても FINALIZED にする")


class PeriodResponse(BaseModel):
    period: Period
    dates: list[str]
    open_dates: list[str] = Field(default_factory=list, description="開校日（日曜・休校日を除く）")
    message: str


class PeriodListResponse(BaseModel):
    periods: list[Period]
    active_period_id: int | None = None


class DaySubmission(BaseModel):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    slots: dict[str, str]

    @field_validator("slots")
    @classmethod
    def validate_slots(cls, slots: dict[str, str]) -> dict[str, str]:
        if set(slots.keys()) != SLOT_KEYS:
            raise ValueError(f'slots must include exactly {sorted(SLOT_KEYS)}')
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
    slots: dict[str, str]
    locked_slots: dict[str, bool] = Field(description="◎ 固定枠は true")
    readonly: bool = False
    confirmed_lessons: list[dict] = Field(default_factory=list, description="確定後の割当")
    teacher_slot_lanes: list[dict] = Field(
        default_factory=list,
        description="講師向け2レーン表示 [{slot, lanes:[{lane, lesson_kind, ...}]}]",
    )


class MyScheduleResponse(BaseModel):
    role: SubmitRole
    entity_id: int
    period_id: int
    period_name: str
    period_start_date: str = ""
    period_end_date: str = ""
    period_status: PeriodStatus
    period_kind: str = "CRAM"
    schedule_requested: bool = False
    schedule_published: bool = False
    submission_complete: bool = False
    resubmit_pending: bool = False
    readonly: bool
    time_slots: list[dict] = Field(default_factory=list)
    subject_plans: list[dict] = Field(default_factory=list, description="生徒希望教科 [{subject, slot_count}]")
    message: str | None = None
    dates: list[ScheduleDay]
    calendar_year: int | None = None
    month: int | None = None


class ShiftImportResponse(BaseModel):
    period_id: int
    imported_count: int
    message: str
