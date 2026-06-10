from datetime import date

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
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
