from typing import Literal

from pydantic import BaseModel, Field, field_validator

from schemas.period import SLOT_KEYS, SlotSymbol

ShiftStatus = Literal[
    "◎", "×", "", "確定", "不足", "未提出", "AI提案", "待機", "不可", "通常授業"
]


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
    slots: dict[str, SlotSymbol] = Field(description='◎=通常授業, ×=不可, ""=空いてる')
    period_id: int | None = None
    period_status: str | None = None
    readonly: bool = False
    locked_slots: dict[str, bool] | None = None


class ShiftSlotUpdateRequest(BaseModel):
    teacher_id: int = Field(ge=1)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    slot: int = Field(ge=1, le=4, description="コマ番号（1〜4）")
    status: SlotSymbol


class ShiftSubmitRequest(BaseModel):
    teacher_id: int = Field(ge=1, description="開発中は 1=田中 先生 など")
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    slots: dict[str, SlotSymbol] = Field(description='キーは "1"〜"4"')

    @field_validator("slots")
    @classmethod
    def validate_slot_keys(cls, slots: dict[str, SlotSymbol]) -> dict[str, SlotSymbol]:
        if set(slots.keys()) != SLOT_KEYS:
            raise ValueError('slots must include exactly "1", "2", "3", and "4"')
        return slots


class ShiftSubmitResponse(BaseModel):
    teacher_id: int
    date: str
    message: str
    dashboard_status: dict[str, ShiftStatus] = Field(
        description="教室長画面向けに変換後の s1〜s4 相当"
    )
