"""送付済みスケジュールへの変更申請（教室長承認制）。"""

from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal
from models import ShiftChangeRequest
from schemas.period import empty_slots
from services.entity_store import get_student, list_teachers
from services.period_store import get_entity_base_day, get_period, open_dates_for_period
from services.schedule_publish_store import (
    is_schedule_published,
    is_teacher_schedule_published,
)
from services.student_plan_store import list_plans_for_student
from services.student_slot_codec import validate_student_slot
from services.submission_store import get_entity_day, upsert_entity_day


def _session() -> Session:
    return SessionLocal()


def _entity_name(role: str, entity_id: int) -> str:
    if role == "student":
        return get_student(entity_id)["name"]
    teacher = next((t for t in list_teachers() if t["id"] == entity_id), None)
    if teacher is None:
        raise HTTPException(status_code=404, detail=f"Teacher id={entity_id} not found")
    return teacher["name"]


def _to_dict(row: ShiftChangeRequest) -> dict:
    return {
        "id": row.id,
        "period_id": row.period_id,
        "role": row.role,
        "entity_id": row.entity_id,
        "entity_name": row.entity_name,
        "date": row.slot_date.isoformat(),
        "slot": int(row.slot_key),
        "current_symbol": row.current_symbol,
        "requested_symbol": row.requested_symbol,
        "reason": row.reason,
        "status": row.status,
    }


def _is_published(period_id: int, role: str, entity_id: int) -> bool:
    if role == "student":
        return is_schedule_published(period_id, entity_id)
    return is_teacher_schedule_published(period_id, entity_id)


def create_change_request(
    period_id: int,
    role: str,
    entity_id: int,
    iso_date: str,
    slot: int,
    requested_symbol: str,
    reason: str = "",
) -> dict:
    period = get_period(period_id)
    if period.status != "FINALIZED" and not _is_published(period_id, role, entity_id):
        raise HTTPException(
            status_code=409,
            detail="スケジュールが未送付のため、変更申請は不要です。直接編集してください。",
        )
    if iso_date not in open_dates_for_period(period):
        raise HTTPException(status_code=400, detail=f"{iso_date} は開校日ではありません")
    if role == "student":
        allowed = {p["subject"] for p in list_plans_for_student(period_id, entity_id)}
        requested_symbol = validate_student_slot(requested_symbol, allowed)
    elif requested_symbol not in ("×", ""):
        raise HTTPException(status_code=400, detail="希望する状態は 空 または × のみ指定できます")

    slot_key = str(slot)
    base = get_entity_base_day(period_id, role, entity_id, iso_date)
    if base.get(slot_key) == "◎":
        raise HTTPException(status_code=409, detail="◎ 通常授業は変更申請できません")

    submitted = get_entity_day(role, entity_id, iso_date) or empty_slots()
    current = submitted.get(slot_key, "")
    if current == requested_symbol:
        raise HTTPException(status_code=409, detail="現在の状態と同じため申請の必要がありません")

    target_date = date.fromisoformat(iso_date)
    with _session() as db:
        duplicate = db.scalars(
            select(ShiftChangeRequest).where(
                ShiftChangeRequest.period_id == period_id,
                ShiftChangeRequest.role == role,
                ShiftChangeRequest.entity_id == entity_id,
                ShiftChangeRequest.slot_date == target_date,
                ShiftChangeRequest.slot_key == slot_key,
                ShiftChangeRequest.status == "PENDING",
            )
        ).first()
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="同じコマの申請が承認待ちです")

        row = ShiftChangeRequest(
            period_id=period_id,
            role=role,
            entity_id=entity_id,
            entity_name=_entity_name(role, entity_id),
            slot_date=target_date,
            slot_key=slot_key,
            current_symbol=current,
            requested_symbol=requested_symbol,
            reason=reason[:500],
            status="PENDING",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _to_dict(row)


def list_change_requests(
    period_id: int,
    *,
    status: str | None = None,
    role: str | None = None,
    entity_id: int | None = None,
) -> list[dict]:
    with _session() as db:
        query = select(ShiftChangeRequest).where(ShiftChangeRequest.period_id == period_id)
        if status:
            query = query.where(ShiftChangeRequest.status == status)
        if role:
            query = query.where(ShiftChangeRequest.role == role)
        if entity_id is not None:
            query = query.where(ShiftChangeRequest.entity_id == entity_id)
        rows = db.scalars(query.order_by(ShiftChangeRequest.id.desc())).all()
    return [_to_dict(row) for row in rows]


def count_pending_requests(period_id: int) -> int:
    with _session() as db:
        rows = db.scalars(
            select(ShiftChangeRequest.id).where(
                ShiftChangeRequest.period_id == period_id,
                ShiftChangeRequest.status == "PENDING",
            )
        ).all()
    return len(rows)


def resolve_change_request(request_id: int, action: str) -> dict:
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action は approve / reject のいずれかです")

    with _session() as db:
        row = db.get(ShiftChangeRequest, request_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"変更申請 id={request_id} が見つかりません")
        if row.status != "PENDING":
            raise HTTPException(status_code=409, detail="この申請は処理済みです")

        row.status = "APPROVED" if action == "approve" else "REJECTED"
        db.commit()
        db.refresh(row)
        result = _to_dict(row)

    if action == "approve":
        iso_date = result["date"]
        slots = get_entity_day(result["role"], result["entity_id"], iso_date) or empty_slots()
        slots[str(result["slot"])] = result["requested_symbol"]  # type: ignore[assignment]
        upsert_entity_day(result["role"], result["entity_id"], iso_date, slots)

    return result
