"""生徒・講師ごとのスケジュール送付（確定）状態。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal
from models import StudentSchedulePublish, TeacherSchedulePublish


def _session() -> Session:
    return SessionLocal()


def is_schedule_published(period_id: int, student_id: int) -> bool:
    with _session() as db:
        row = db.scalars(
            select(StudentSchedulePublish).where(
                StudentSchedulePublish.period_id == period_id,
                StudentSchedulePublish.student_id == student_id,
            )
        ).first()
    return row is not None


def list_published_student_ids(period_id: int) -> set[int]:
    with _session() as db:
        rows = db.scalars(
            select(StudentSchedulePublish.student_id).where(
                StudentSchedulePublish.period_id == period_id
            )
        ).all()
    return set(rows)


def publish_student_schedule(period_id: int, student_id: int) -> bool:
    """確定送信。既に確定済みなら False。"""
    with _session() as db:
        existing = db.scalars(
            select(StudentSchedulePublish).where(
                StudentSchedulePublish.period_id == period_id,
                StudentSchedulePublish.student_id == student_id,
            )
        ).first()
        if existing is not None:
            return False
        db.add(StudentSchedulePublish(period_id=period_id, student_id=student_id))
        db.commit()
        return True


def is_teacher_schedule_published(period_id: int, teacher_id: int) -> bool:
    with _session() as db:
        row = db.scalars(
            select(TeacherSchedulePublish).where(
                TeacherSchedulePublish.period_id == period_id,
                TeacherSchedulePublish.teacher_id == teacher_id,
            )
        ).first()
    return row is not None


def list_published_teacher_ids(period_id: int) -> set[int]:
    with _session() as db:
        rows = db.scalars(
            select(TeacherSchedulePublish.teacher_id).where(
                TeacherSchedulePublish.period_id == period_id
            )
        ).all()
    return set(rows)


def publish_teacher_schedule(period_id: int, teacher_id: int) -> bool:
    """講師への送付。既に送付済みなら False。"""
    with _session() as db:
        existing = db.scalars(
            select(TeacherSchedulePublish).where(
                TeacherSchedulePublish.period_id == period_id,
                TeacherSchedulePublish.teacher_id == teacher_id,
            )
        ).first()
        if existing is not None:
            return False
        db.add(TeacherSchedulePublish(period_id=period_id, teacher_id=teacher_id))
        db.commit()
        return True


def publish_all_schedules(period_id: int) -> dict:
    """割当済みの生徒・全講師にスケジュールを一括送付。"""
    from services.assignment_sheets import build_assignment_sheets

    sheets = build_assignment_sheets(period_id)
    students_published = 0
    students_skipped: list[str] = []
    for student in sheets["students"]:
        if student["pending_count"] > 0:
            students_skipped.append(student["name"])
            continue
        if publish_student_schedule(period_id, student["id"]):
            students_published += 1

    teachers_published = 0
    for teacher in sheets["teachers"]:
        if publish_teacher_schedule(period_id, teacher["id"]):
            teachers_published += 1

    return {
        "period_id": period_id,
        "students_published": students_published,
        "students_skipped": students_skipped,
        "teachers_published": teachers_published,
    }
