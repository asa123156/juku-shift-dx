from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class AppSetting(Base):
    """アプリ全体のキー・値設定（active_period_id など）"""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)


class Period(Base):
    """募集期間（DRAFT → COLLECTING → FINALIZED）"""

    __tablename__ = "periods"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    closed_dates: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_deleted: Mapped[int] = mapped_column(nullable=False, default=0)
    location_slug: Mapped[str] = mapped_column(String(64), nullable=False, default="hakutei")
    period_kind: Mapped[str] = mapped_column(String(10), nullable=False, default="CRAM")
    submission_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)


class PeriodBaseSlot(Base):
    """期間ごとの ◎ 固定枠（講師・生徒）"""

    __tablename__ = "period_base_slots"
    __table_args__ = (
        UniqueConstraint(
            "period_id",
            "role",
            "entity_id",
            "slot_date",
            "slot_key",
            name="uq_period_base_slot",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    entity_id: Mapped[int] = mapped_column(nullable=False)
    slot_date: Mapped[date] = mapped_column(Date, nullable=False)
    slot_key: Mapped[str] = mapped_column(String(1), nullable=False)
    symbol: Mapped[str] = mapped_column(String(2), nullable=False, default="")


class AdminOverride(Base):
    """教室長によるコマ上書き（確定・AI提案 等）"""

    __tablename__ = "admin_overrides"
    __table_args__ = (
        UniqueConstraint(
            "teacher_id",
            "slot_date",
            "slot_key",
            name="uq_admin_override",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(nullable=False, index=True)
    slot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    slot_key: Mapped[str] = mapped_column(String(1), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)


class ShiftSubmission(Base):
    """講師・生徒のシフト提出（日付 × コマ）"""

    __tablename__ = "shift_submissions"
    __table_args__ = (
        UniqueConstraint(
            "role",
            "entity_id",
            "slot_date",
            "slot_key",
            name="uq_shift_submission",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(nullable=False)
    slot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    slot_key: Mapped[str] = mapped_column(String(1), nullable=False)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False, default="")


class Assignment(Base):
    """確定した割当（生徒 × 講師 × コマ）— 互換用。新規は class_schedules を正本とする。"""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(nullable=False)
    student_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    teacher_id: Mapped[int] = mapped_column(nullable=False)
    teacher_name: Mapped[str] = mapped_column(String(255), nullable=False)
    slot: Mapped[int] = mapped_column(nullable=False)
    lesson_kind: Mapped[str] = mapped_column(String(10), nullable=False, default="講習")


class ClassSchedule(Base):
    """時間割表の正本。is_fixed=True が通常授業（常に◎）、False が講習枠。"""

    __tablename__ = "class_schedules"
    __table_args__ = (
        UniqueConstraint(
            "period_id",
            "slot_date",
            "teacher_id",
            "slot",
            "student_id",
            name="uq_class_schedule",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), nullable=False, index=True)
    slot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    slot: Mapped[int] = mapped_column(nullable=False)
    teacher_id: Mapped[int] = mapped_column(nullable=False, index=True)
    teacher_name: Mapped[str] = mapped_column(String(255), nullable=False)
    student_id: Mapped[int] = mapped_column(nullable=False, index=True)
    student_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_fixed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    lesson_type: Mapped[str | None] = mapped_column(String(20), nullable=True)


class TeacherSlotCapacity(Base):
    """講師コマごとの授業形態（1対2=2レーン / 1対4=4レーン）"""

    __tablename__ = "teacher_slot_capacities"
    __table_args__ = (
        UniqueConstraint(
            "teacher_id",
            "slot_date",
            "slot",
            name="uq_teacher_slot_capacity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(nullable=False, index=True)
    slot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    slot: Mapped[int] = mapped_column(nullable=False)
    max_lanes: Mapped[int] = mapped_column(nullable=False, default=2)


class AssignmentRequest(Base):
    """未割当の割当リクエスト（日付 × 生徒 × 教科）"""

    __tablename__ = "assignment_requests"
    __table_args__ = (
        UniqueConstraint(
            "slot_date",
            "student_id",
            "subject",
            name="uq_assignment_request",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(nullable=False)
    student_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)


class StudentSubjectPlan(Base):
    """講習期間ごとの生徒希望（教科 × コマ数）— 教室長が設定"""

    __tablename__ = "student_subject_plans"
    __table_args__ = (
        UniqueConstraint(
            "period_id",
            "student_id",
            "subject",
            name="uq_student_subject_plan",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    slot_count: Mapped[int] = mapped_column(nullable=False, default=1)
    teacher_id: Mapped[int | None] = mapped_column(nullable=True, index=True)


class ShiftDashboard(Base):
    """日別シフトダッシュボードのベースデータ"""

    __tablename__ = "shift_dashboards"

    slot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    display_date: Mapped[str] = mapped_column(String(255), nullable=False)
    time_slots: Mapped[list] = mapped_column(JSON, nullable=False)
    teachers: Mapped[list] = mapped_column(JSON, nullable=False)


class StudentProfile(Base):
    """生徒マスタ（学年・校種付き）"""

    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    school_level: Mapped[str] = mapped_column(String(20), nullable=False, default="middle")
    grade_year: Mapped[int] = mapped_column(nullable=False, default=1)


class TeacherProfile(Base):
    """講師マスタ"""

    __tablename__ = "teacher_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    color: Mapped[str] = mapped_column(String(64), nullable=False, default="bg-blue-100 text-blue-600")


class StudentSchedulePublish(Base):
    """生徒ごとのスケジュール確定（教室長が送信）"""

    __tablename__ = "student_schedule_publishes"
    __table_args__ = (
        UniqueConstraint("period_id", "student_id", name="uq_student_schedule_publish"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(nullable=False, index=True)


class StudentScheduleRequestPublish(Base):
    """生徒ごとの初回提案書送付（回答依頼）。"""

    __tablename__ = "student_schedule_request_publishes"
    __table_args__ = (
        UniqueConstraint("period_id", "student_id", name="uq_student_schedule_request_publish"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(nullable=False, index=True)


class TeacherSchedulePublish(Base):
    """講師ごとのスケジュール送付（教室長が送信）"""

    __tablename__ = "teacher_schedule_publishes"
    __table_args__ = (
        UniqueConstraint("period_id", "teacher_id", name="uq_teacher_schedule_publish"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), nullable=False, index=True)
    teacher_id: Mapped[int] = mapped_column(nullable=False, index=True)


class TeacherScheduleRequestPublish(Base):
    """講師ごとの初回提案書送付（回答依頼）。"""

    __tablename__ = "teacher_schedule_request_publishes"
    __table_args__ = (
        UniqueConstraint("period_id", "teacher_id", name="uq_teacher_schedule_request_publish"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), nullable=False, index=True)
    teacher_id: Mapped[int] = mapped_column(nullable=False, index=True)


class PeriodScheduleWorkbook(Base):
    """講習期間ごとにインポートした月次時間割 Excel（ダウンロード時に編集して返す）"""

    __tablename__ = "period_schedule_workbooks"

    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, default="schedule.xlsx")
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)


class ShiftChangeRequest(Base):
    """送付済みスケジュールへの変更申請（教室長の承認が必要）"""

    __tablename__ = "shift_change_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    entity_id: Mapped[int] = mapped_column(nullable=False, index=True)
    entity_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    slot_date: Mapped[date] = mapped_column(Date, nullable=False)
    slot_key: Mapped[str] = mapped_column(String(1), nullable=False)
    current_symbol: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    requested_symbol: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    reason: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="PENDING", index=True)
    request_type: Mapped[str] = mapped_column(String(20), nullable=False, default="SLOT")
