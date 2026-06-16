"""講習期間ごとの生徒希望（教科・コマ数）と割当リクエスト同期。"""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from database import SessionLocal
from models import AssignmentRequest as AssignmentRequestRow
from models import StudentSubjectPlan
from services.assignment_store import append_assignment_requests
from services.entity_store import get_student
from services.period_store import get_period, open_dates_for_period


def _session() -> Session:
    return SessionLocal()


def _plan_to_dict(row: StudentSubjectPlan) -> dict:
    return {
        "subject": row.subject,
        "slot_count": int(row.slot_count),
    }


def list_plans_for_period(period_id: int) -> dict[int, list[dict]]:
    """student_id -> [{subject, slot_count}, ...]"""
    with _session() as db:
        rows = db.scalars(
            select(StudentSubjectPlan)
            .where(StudentSubjectPlan.period_id == period_id)
            .order_by(StudentSubjectPlan.student_id, StudentSubjectPlan.subject)
        ).all()
    result: dict[int, list[dict]] = {}
    for row in rows:
        result.setdefault(row.student_id, []).append(_plan_to_dict(row))
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
    return [_plan_to_dict(row) for row in rows]


def save_student_plans(period_id: int, student_id: int, plans: list[dict]) -> list[dict]:
    period = get_period(period_id)
    if period.status == "FINALIZED":
        raise HTTPException(status_code=409, detail="確定済みの講習期間は希望を変更できません")
    get_student(student_id)

    cleaned: list[tuple[str, int]] = []
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
        if count > 0:
            cleaned.append((subject, count))

    with _session() as db:
        db.execute(
            delete(StudentSubjectPlan).where(
                StudentSubjectPlan.period_id == period_id,
                StudentSubjectPlan.student_id == student_id,
            )
        )
        for subject, slot_count in cleaned:
            db.add(
                StudentSubjectPlan(
                    period_id=period_id,
                    student_id=student_id,
                    subject=subject,
                    slot_count=slot_count,
                )
            )
        db.commit()

    synced = sync_student_assignment_requests(period_id, student_id)
    return list_plans_for_student(period_id, student_id), synced


def _build_requests_by_date(
    open_dates: list[str],
    student_id: int,
    student_name: str,
    plans: list[dict],
) -> dict[str, list[dict]]:
    """希望コマ数を開校日に分散（1日1教科1件まで）。"""
    if not open_dates or not plans:
        return {d: [] for d in open_dates}

    by_date: dict[str, list[dict]] = {d: [] for d in open_dates}
    n = len(open_dates)
    day_ptr = 0

    for plan in plans:
        subject = plan["subject"]
        need = int(plan["slot_count"])
        placed = 0
        attempts = 0
        max_attempts = n * max(need, 1) + n
        while placed < need and attempts < max_attempts:
            iso = open_dates[day_ptr % n]
            day_ptr += 1
            attempts += 1
            if any(r["subject"] == subject for r in by_date[iso]):
                continue
            by_date[iso].append(
                {
                    "student_id": student_id,
                    "student_name": student_name,
                    "subject": subject,
                }
            )
            placed += 1

    return by_date


def sync_student_assignment_requests(period_id: int, student_id: int) -> int:
    """生徒の希望から assignment_requests を再生成。戻り値: 作成件数。"""
    period = get_period(period_id)
    open_dates = open_dates_for_period(period)
    if not open_dates:
        return 0

    student = get_student(student_id)
    plans = list_plans_for_student(period_id, student_id)
    by_date = _build_requests_by_date(open_dates, student_id, student["name"], plans)

    start_d = date.fromisoformat(open_dates[0])
    end_d = date.fromisoformat(open_dates[-1])
    with _session() as db:
        db.execute(
            delete(AssignmentRequestRow).where(
                AssignmentRequestRow.student_id == student_id,
                AssignmentRequestRow.slot_date >= start_d,
                AssignmentRequestRow.slot_date <= end_d,
            )
        )
        db.commit()

    total = 0
    for iso in open_dates:
        reqs = by_date.get(iso, [])
        if not reqs:
            continue
        added, _ = append_assignment_requests(iso, reqs)
        total += added
    return total


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
