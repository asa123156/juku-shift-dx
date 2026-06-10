from typing import Literal

from pydantic import BaseModel, Field, field_validator

ShiftStatus = Literal["確定", "待機", "不可", "不足", "未提出", "AI提案", "◎"]
AvailabilityStatus = Literal["priority", "available", "unavailable", "blank"]


class TimeSlotInfo(BaseModel):
    slot: int = Field(ge=1, le=8, description="コマ番号（1始まり）")
    label: str = Field(description="表示用ラベル（例: 1コマ）")
    start: str = Field(description="開始時刻 HH:MM")
    end: str = Field(description="終了時刻 HH:MM")


class DashboardMetrics(BaseModel):
    unsubmitted_teachers: int = Field(ge=0, description="未提出の講師数")
    shortage_slots: int = Field(ge=0, description="不足しているコマ数")


class TeacherShiftRow(BaseModel):
    id: int
    name: str
    color: str = Field(description="Tailwind のクラス名（アバター用）")
    s1: ShiftStatus
    s2: ShiftStatus
    s3: ShiftStatus
    s4: ShiftStatus


class ShiftDashboardResponse(BaseModel):
    date: str = Field(description="ISO日付 YYYY-MM-DD")
    display_date: str = Field(description="画面ヘッダー用の表示文言")
    metrics: DashboardMetrics
    time_slots: list[TimeSlotInfo]
    teachers: list[TeacherShiftRow]


class TeacherShiftSubmissionResponse(BaseModel):
    teacher_id: int
    date: str
    slots: dict[str, AvailabilityStatus] = Field(
        description='コマ番号をキーにした可否（"priority"=◎, "available"=○, "unavailable"=×, "blank"=未入力）'
    )


class ShiftSlotUpdateRequest(BaseModel):
    teacher_id: int = Field(ge=1)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    slot: int = Field(ge=1, le=4, description="コマ番号（1〜4）")
    status: AvailabilityStatus


class ShiftSubmitRequest(BaseModel):
    teacher_id: int = Field(ge=1, description="開発中は 1=田中 先生 など")
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    slots: dict[str, AvailabilityStatus] = Field(
        description='キーは "1"〜"4"（フロントの slot1 → "1"）'
    )

    @field_validator("slots")
    @classmethod
    def validate_slot_keys(cls, slots: dict[str, AvailabilityStatus]) -> dict[str, AvailabilityStatus]:
        required = {"1", "2", "3", "4"}
        if set(slots.keys()) != required:
            raise ValueError('slots must include exactly "1", "2", "3", and "4"')
        return slots


class ShiftSubmitResponse(BaseModel):
    teacher_id: int
    date: str
    message: str
    dashboard_status: dict[str, ShiftStatus] = Field(
        description="教室長画面向けに変換後の s1〜s4 相当"
    )
