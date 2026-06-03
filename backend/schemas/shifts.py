from typing import Literal

from pydantic import BaseModel, Field

ShiftStatus = Literal["確定", "待機", "不可", "不足", "未提出"]


class TimeSlotInfo(BaseModel):
    slot: int = Field(ge=1, le=8, description="コマ番号（1始まり）")
    label: str = Field(description="表示用ラベル（例: 1コマ）")
    start: str = Field(description="開始時刻 HH:MM")
    end: str = Field(description="終了時刻 HH:MM")


class DashboardMetrics(BaseModel):
    unsubmitted_teachers: int = Field(ge=0, description="未提出の講師数")
    shortage_slots: int = Field(ge=0, description="不足しているコマ数")


class TeacherShiftRow(BaseModel):
    """教室長ダッシュボードの表1行分（フロントの teachers state と同型）"""

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
