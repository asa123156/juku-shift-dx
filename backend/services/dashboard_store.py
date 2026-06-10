import json
from datetime import date
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import DASHBOARDS_DIR, REPO_ROOT
from database import SessionLocal
from models import ShiftDashboard as ShiftDashboardRow

_EMPTY_METRICS = {"unsubmitted_teachers": 0, "shortage_slots": 0}


def _session() -> Session:
    return SessionLocal()


def _row_to_dict(row: ShiftDashboardRow) -> dict:
    return {
        "date": row.slot_date.isoformat(),
        "display_date": row.display_date,
        "metrics": dict(_EMPTY_METRICS),
        "time_slots": row.time_slots,
        "teachers": row.teachers,
    }


def _load_json_dashboard(path: Path) -> dict:
    if not path.is_file():
        raise HTTPException(
            status_code=500,
            detail=f"Data file not found: {path.relative_to(REPO_ROOT)}",
        )
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=f"{path.name} must be a JSON object")
    return data


def _import_dashboard(db: Session, data: dict) -> None:
    iso_date = data["date"]
    db.merge(
        ShiftDashboardRow(
            slot_date=date.fromisoformat(iso_date),
            display_date=data["display_date"],
            time_slots=data["time_slots"],
            teachers=data["teachers"],
        )
    )


def seed_shift_dashboards_if_empty() -> None:
    """DB が空のとき shift-dashboards/*.json からベースデータを投入する。"""
    with _session() as db:
        if db.scalar(select(ShiftDashboardRow.slot_date).limit(1)) is not None:
            return
        if not DASHBOARDS_DIR.is_dir():
            return
        for path in sorted(DASHBOARDS_DIR.glob("*.json")):
            _import_dashboard(db, _load_json_dashboard(path))
        db.commit()


def reset_shift_dashboards_for_tests() -> None:
    """テスト用: ダッシュボードを JSON ファイルから再投入する。"""
    from database import Base, engine

    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with _session() as db:
        db.query(ShiftDashboardRow).delete()
        if DASHBOARDS_DIR.is_dir():
            for path in sorted(DASHBOARDS_DIR.glob("*.json")):
                _import_dashboard(db, _load_json_dashboard(path))
        db.commit()


def list_shift_dates() -> list[str]:
    with _session() as db:
        rows = db.scalars(select(ShiftDashboardRow.slot_date).order_by(ShiftDashboardRow.slot_date)).all()
    return [row.isoformat() for row in rows]


def load_shift_dashboard_base(iso_date: str) -> dict:
    target_date = date.fromisoformat(iso_date)
    with _session() as db:
        row = db.get(ShiftDashboardRow, target_date)
    if row is None:
        raise HTTPException(
            status_code=500,
            detail=f"Shift dashboard not found for date={iso_date}",
        )
    if row.slot_date.isoformat() != iso_date:
        raise HTTPException(
            status_code=500,
            detail=f"Dashboard date mismatch: expected {iso_date}",
        )
    return _row_to_dict(row)
