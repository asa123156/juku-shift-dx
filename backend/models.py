from datetime import date

from sqlalchemy import JSON, Date, ForeignKey, String, UniqueConstraint
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
    symbol: Mapped[str] = mapped_column(String(2), nullable=False, default="")


class Assignment(Base):
    """確定した割当（生徒 × 講師 × コマ）"""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(nullable=False)
    student_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    teacher_id: Mapped[int] = mapped_column(nullable=False)
    teacher_name: Mapped[str] = mapped_column(String(255), nullable=False)
    slot: Mapped[int] = mapped_column(nullable=False)


class AssignmentRequest(Base):
    """未割当の割当リクエスト（CSV 取込）"""

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


class ShiftDashboard(Base):
    """日別シフトダッシュボードのベースデータ"""

    __tablename__ = "shift_dashboards"

    slot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    display_date: Mapped[str] = mapped_column(String(255), nullable=False)
    time_slots: Mapped[list] = mapped_column(JSON, nullable=False)
    teachers: Mapped[list] = mapped_column(JSON, nullable=False)
