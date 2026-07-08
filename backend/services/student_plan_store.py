"""講習期間ごとの生徒希望（教科・コマ数・担当講師）と割当リクエスト同期。"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from database import SessionLocal
from models import StudentSubjectPlan
from services.assignment_store import get_assignments_between
from services.entity_store import get_student, list_teachers
from services.period_store import get_period


def _session() -> Session:
    return SessionLocal()


def _teacher_name_map() -> dict[int, str]:
    return {t["id"]: t["name"] for t in list_teachers()}


def _plan_to_dict(row: StudentSubjectPlan, teacher_names: dict[int, str] | None = None) -> dict:
    names = teacher_names if teacher_names is not None else _teacher_name_map()
    teacher_id = row.teacher_id
    return {
        "subject": row.subject,
        "slot_count": int(row.slot_count),
        "teacher_id": teacher_id,
        "teacher_name": names.get(teacher_id, "") if teacher_id else None,
    }


def list_plans_for_period(period_id: int) -> dict[int, list[dict]]:
    """student_id -> [{subject, slot_count, teacher_id, teacher_name}, ...]"""
    teacher_names = _teacher_name_map()
    with _session() as db:
        rows = db.scalars(
            select(StudentSubjectPlan)
            .where(StudentSubjectPlan.period_id == period_id)
            .order_by(StudentSubjectPlan.student_id, StudentSubjectPlan.subject)
        ).all()
    result: dict[int, list[dict]] = {}
    for row in rows:
        result.setdefault(row.student_id, []).append(_plan_to_dict(row, teacher_names))
    return result


def list_plans_for_student(period_id: int, student_id: int) -> list[dict]:
    with _session() as db:
        rows = db.scalars(
            select(StudentSubjectPlan)
            .where(
                StudentSubjectPlan.period_id == period_id,
                StudentSubjectPlan.student_id == student_id,
            )
            .order_by(StudentSubjectPlan.subject)
        ).all()
    teacher_names = _teacher_name_map()
    return [_plan_to_dict(row, teacher_names) for row in rows]


def get_preferred_teacher_id(period_id: int, student_id: int, subject: str) -> int | None:
    for plan in list_plans_for_student(period_id, student_id):
        if plan["subject"] == subject and plan.get("teacher_id"):
            return int(plan["teacher_id"])
    return None


def _parse_teacher_id(raw: object) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        teacher_id = int(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="担当講師の指定が不正です") from exc
    if teacher_id < 1:
        return None
    if teacher_id not in _teacher_name_map():
        raise HTTPException(status_code=404, detail=f"講師 id={teacher_id} が見つかりません")
    return teacher_id


def save_student_plans(period_id: int, student_id: int, plans: list[dict]) -> list[dict]:
    period = get_period(period_id)
    if period.status == "FINALIZED":
        raise HTTPException(status_code=409, detail="確定済みの講習期間は希望を変更できません")
    get_student(student_id)

    cleaned: list[tuple[str, int, int | None]] = []
    seen: set[str] = set()
    for item in plans:
        subject = str(item.get("subject", "")).strip()
        if not subject:
            continue
        if subject in seen:
            raise HTTPException(status_code=400, detail=f"教科「{subject}」が重複しています")
        seen.add(subject)
        try:
            count = int(item.get("slot_count", 0))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="コマ数は整数で指定してください") from exc
        if count < 0:
            raise HTTPException(status_code=400, detail="コマ数は0以上にしてください")
        teacher_id = _parse_teacher_id(item.get("teacher_id"))
        if count > 0:
            cleaned.append((subject, count, teacher_id))

    with _session() as db:
        db.execute(
            delete(StudentSubjectPlan).where(
                StudentSubjectPlan.period_id == period_id,
                StudentSubjectPlan.student_id == student_id,
            )
        )
        for subject, slot_count, teacher_id in cleaned:
            db.add(
                StudentSubjectPlan(
                    period_id=period_id,
                    student_id=student_id,
                    subject=subject,
                    slot_count=slot_count,
                    teacher_id=teacher_id,
                )
            )
        db.commit()

    synced = sync_student_assignment_requests(period_id, student_id)
    return list_plans_for_student(period_id, student_id), synced


def sync_student_assignment_requests(period_id: int, student_id: int) -> int:
    """希望と割当の差分から未割当件数を返す（日付への事前分散は行わない）。"""
    from services.schedule_canonical import compute_student_pending_count

    period = get_period(period_id)
    plans = list_plans_for_student(period_id, student_id)
    assignments = get_assignments_between(period.start_date, period.end_date)
    return compute_student_pending_count(student_id, plans, assignments)


def delete_plans_for_student(period_id: int, student_id: int) -> None:
    with _session() as db:
        db.execute(
            delete(StudentSubjectPlan).where(
                StudentSubjectPlan.period_id == period_id,
                StudentSubjectPlan.student_id == student_id,
            )
        )
        db.commit()


def reset_student_plans_for_tests() -> None:
    with _session() as db:
        db.query(StudentSubjectPlan).delete()
        db.commit()
