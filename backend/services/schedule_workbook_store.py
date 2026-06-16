"""講習期間ごとの月次時間割 Excel バイナリの保存・取得。"""

from __future__ import annotations

from datetime import datetime

from database import SessionLocal
from models import PeriodScheduleWorkbook


def save_period_workbook(period_id: int, filename: str, content: bytes) -> None:
    safe_name = (filename or "schedule.xlsx").strip() or "schedule.xlsx"
    with SessionLocal() as db:
        row = db.get(PeriodScheduleWorkbook, period_id)
        if row is None:
            db.add(
                PeriodScheduleWorkbook(
                    period_id=period_id,
                    filename=safe_name,
                    content=content,
                    imported_at=datetime.utcnow(),
                )
            )
        else:
            row.filename = safe_name
            row.content = content
            row.imported_at = datetime.utcnow()
        db.commit()


def get_period_workbook(period_id: int) -> tuple[bytes, str] | None:
    with SessionLocal() as db:
        row = db.get(PeriodScheduleWorkbook, period_id)
        if row is None:
            return None
        return bytes(row.content), row.filename


def reset_period_workbooks_for_tests() -> None:
    with SessionLocal() as db:
        db.query(PeriodScheduleWorkbook).delete()
        db.commit()
