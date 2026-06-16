import json
from copy import deepcopy
from datetime import date
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import DATA_DIR
from database import SessionLocal
from models import Assignment as AssignmentRow
from models import AssignmentRequest as AssignmentRequestRow
from schemas.assignment import AssignmentRecord

ASSIGNMENTS_PATH = DATA_DIR / "assignments.json"
REQUESTS_PATH = DATA_DIR / "assignment-requests.json"


def _session() -> Session:
    return SessionLocal()


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=f"{path.name} must be a JSON object")
    return data


def _assignment_to_dict(row: AssignmentRow) -> dict:
    return {
        "date": row.slot_date.isoformat(),
        "student_id": row.student_id,
        "student_name": row.student_name,
        "subject": row.subject,
        "teacher_id": row.teacher_id,
        "teacher_name": row.teacher_name,
        "slot": row.slot,
    }


def _request_to_dict(row: AssignmentRequestRow) -> dict:
    return {
        "student_id": row.student_id,
        "student_name": row.student_name,
        "subject": row.subject,
    }


def _import_assignments_from_json(db: Session, raw: dict) -> None:
    for iso_date, rows in raw.items():
        if not isinstance(rows, list):
            continue
        slot_date = date.fromisoformat(iso_date)
        for item in rows:
            db.add(
                AssignmentRow(
                    slot_date=slot_date,
                    student_id=int(item["student_id"]),
                    student_name=item["student_name"],
                    subject=item["subject"],
                    teacher_id=int(item["teacher_id"]),
                    teacher_name=item["teacher_name"],
                    slot=int(item["slot"]),
                )
            )


def _import_requests_from_json(db: Session, raw: dict) -> None:
    for iso_date, rows in raw.items():
        if not isinstance(rows, list):
            continue
        slot_date = date.fromisoformat(iso_date)
        for item in rows:
            db.add(
                AssignmentRequestRow(
                    slot_date=slot_date,
                    student_id=int(item["student_id"]),
                    student_name=item["student_name"],
                    subject=item["subject"],
                )
            )


def seed_assignments_if_empty() -> None:
    """DB が空のとき assignments.json から確定割当を投入する。"""
    with _session() as db:
        if db.scalar(select(AssignmentRow.id).limit(1)) is not None:
            return
        raw = _read_json(ASSIGNMENTS_PATH)
        if not raw:
            return
        _import_assignments_from_json(db, raw)
        db.commit()


def seed_assignment_requests_if_empty() -> None:
    """DB が空のとき assignment-requests.json から割当リクエストを投入する。"""
    with _session() as db:
        if db.scalar(select(AssignmentRequestRow.id).limit(1)) is not None:
            return
        raw = _read_json(REQUESTS_PATH)
        if not raw:
            return
        _import_requests_from_json(db, raw)
        db.commit()


def reset_assignments_for_tests() -> None:
    """テスト用: 割当データをすべて削除する。"""
    from database import Base, engine

    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with _session() as db:
        db.query(AssignmentRow).delete()
        db.query(AssignmentRequestRow).delete()
        db.commit()


def reset_assignments_from_json() -> tuple[int, int]:
    """デモ用: assignments.json / assignment-requests.json から再投入する。"""
    reset_assignments_for_tests()
    raw_a = _read_json(ASSIGNMENTS_PATH)
    raw_r = _read_json(REQUESTS_PATH)
    assign_count = 0
    request_count = 0
    with _session() as db:
        if raw_a:
            _import_assignments_from_json(db, raw_a)
            assign_count = sum(len(v) for v in raw_a.values() if isinstance(v, list))
        if raw_r:
            _import_requests_from_json(db, raw_r)
            request_count = sum(len(v) for v in raw_r.values() if isinstance(v, list))
        db.commit()
    return assign_count, request_count


def get_assignments_between(start: str, end: str) -> list[dict]:
    start_d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    with _session() as db:
        rows = db.scalars(
            select(AssignmentRow)
            .where(AssignmentRow.slot_date >= start_d, AssignmentRow.slot_date <= end_d)
            .order_by(AssignmentRow.id)
        ).all()
    return deepcopy([_assignment_to_dict(row) for row in rows])


def get_assignments_for_date(iso_date: str) -> list[dict]:
    target_date = date.fromisoformat(iso_date)
    with _session() as db:
        rows = db.scalars(
            select(AssignmentRow)
            .where(AssignmentRow.slot_date == target_date)
            .order_by(AssignmentRow.id)
        ).all()
    return deepcopy([_assignment_to_dict(row) for row in rows])


def get_assignment_requests_for_date(iso_date: str) -> list[dict]:
    target_date = date.fromisoformat(iso_date)
    with _session() as db:
        rows = db.scalars(
            select(AssignmentRequestRow)
            .where(AssignmentRequestRow.slot_date == target_date)
            .order_by(AssignmentRequestRow.id)
        ).all()
    return deepcopy([_request_to_dict(row) for row in rows])


def save_assignments_for_date(iso_date: str, assignments: list[dict]) -> None:
    target_date = date.fromisoformat(iso_date)
    with _session() as db:
        db.query(AssignmentRow).filter(AssignmentRow.slot_date == target_date).delete(
            synchronize_session=False
        )
        for item in assignments:
            db.add(
                AssignmentRow(
                    slot_date=target_date,
                    student_id=int(item["student_id"]),
                    student_name=item["student_name"],
                    subject=item["subject"],
                    teacher_id=int(item["teacher_id"]),
                    teacher_name=item["teacher_name"],
                    slot=int(item["slot"]),
                )
            )
        db.commit()


def add_assignment(record: AssignmentRecord) -> None:
    with _session() as db:
        db.add(
            AssignmentRow(
                slot_date=date.fromisoformat(record.date),
                student_id=record.student_id,
                student_name=record.student_name,
                subject=record.subject,
                teacher_id=record.teacher_id,
                teacher_name=record.teacher_name,
                slot=record.slot,
            )
        )
        db.commit()


def remove_assignment_at_slot(
    iso_date: str,
    teacher_id: int,
    slot: int,
    student_id: int | None = None,
) -> None:
    target_date = date.fromisoformat(iso_date)
    with _session() as db:
        query = db.query(AssignmentRow).filter(
            AssignmentRow.slot_date == target_date,
            AssignmentRow.teacher_id == teacher_id,
            AssignmentRow.slot == slot,
        )
        if student_id is not None:
            query = query.filter(AssignmentRow.student_id == student_id)
        query.delete(synchronize_session=False)
        db.commit()


def cancel_assignment_at_slot(
    iso_date: str,
    teacher_id: int,
    slot: int,
    student_id: int | None = None,
) -> dict | None:
    """割当を解除し、未割当リクエストに戻す。"""
    target_date = date.fromisoformat(iso_date)
    with _session() as db:
        query = select(AssignmentRow).where(
            AssignmentRow.slot_date == target_date,
            AssignmentRow.teacher_id == teacher_id,
            AssignmentRow.slot == slot,
        )
        if student_id is not None:
            query = query.where(AssignmentRow.student_id == student_id)
        row = db.scalars(query).first()
        if row is None:
            return None
        record = _assignment_to_dict(row)
        db.delete(row)
        db.commit()
    append_assignment_requests(
        iso_date,
        [
            {
                "student_id": record["student_id"],
                "student_name": record["student_name"],
                "subject": record["subject"],
            }
        ],
    )
    return record


def clear_requests_fulfilled(iso_date: str, fulfilled_student_ids: set[int]) -> None:
    if not fulfilled_student_ids:
        return
    target_date = date.fromisoformat(iso_date)
    with _session() as db:
        db.query(AssignmentRequestRow).filter(
            AssignmentRequestRow.slot_date == target_date,
            AssignmentRequestRow.student_id.in_(fulfilled_student_ids),
        ).delete(synchronize_session=False)
        db.commit()


def clear_request_fulfilled(iso_date: str, student_id: int, subject: str) -> None:
    target_date = date.fromisoformat(iso_date)
    with _session() as db:
        db.query(AssignmentRequestRow).filter(
            AssignmentRequestRow.slot_date == target_date,
            AssignmentRequestRow.student_id == student_id,
            AssignmentRequestRow.subject == subject,
        ).delete(synchronize_session=False)
        db.commit()


def append_assignment_requests(iso_date: str, requests: list[dict]) -> tuple[int, int]:
    """リクエストを追加する。戻り値: (追加件数, スキップ件数)"""
    target_date = date.fromisoformat(iso_date)
    with _session() as db:
        existing = db.scalars(
            select(AssignmentRequestRow).where(AssignmentRequestRow.slot_date == target_date)
        ).all()
        existing_keys = {(row.student_id, row.subject) for row in existing}
        added = 0
        skipped = 0
        for req in requests:
            key = (req["student_id"], req["subject"])
            if key in existing_keys:
                skipped += 1
                continue
            db.add(
                AssignmentRequestRow(
                    slot_date=target_date,
                    student_id=req["student_id"],
                    student_name=req["student_name"],
                    subject=req["subject"],
                )
            )
            existing_keys.add(key)
            added += 1
        db.commit()
    return added, skipped
