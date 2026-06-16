"""生徒・講師マスタの CRUD と学年ラベル。"""

import json
import re
from copy import deepcopy

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import DATA_DIR
from database import SessionLocal
from models import AdminOverride, Assignment as AssignmentRow
from models import AssignmentRequest as AssignmentRequestRow
from models import ShiftDashboard as ShiftDashboardRow
from models import ShiftSubmission
from models import StudentProfile, TeacherProfile
from models import StudentSubjectPlan

STUDENTS_PATH = DATA_DIR / "students.json"
TEACHERS_PATH = DATA_DIR / "teachers.json"

SchoolLevel = str  # elementary | middle | high

LEVEL_LABELS = {
    "elementary": "小",
    "middle": "中",
    "high": "高",
}

LEVEL_FULL = {
    "elementary": "小学部",
    "middle": "中学部",
    "high": "高校部",
}

TEACHER_COLORS = [
    "bg-blue-100 text-blue-600",
    "bg-pink-100 text-pink-600",
    "bg-green-100 text-green-600",
    "bg-amber-100 text-amber-600",
    "bg-purple-100 text-purple-600",
]


def _session() -> Session:
    return SessionLocal()


def grade_label(school_level: str, grade_year: int) -> str:
    prefix = LEVEL_LABELS.get(school_level, "")
    return f"{prefix}{grade_year}"


_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
_GRADE_LABEL_RE = re.compile(r"^(小|中|高)([0-9]+)")
_LEVEL_FROM_CHAR = {"小": "elementary", "中": "middle", "高": "high"}


def parse_grade_label(label: str) -> tuple[str, int]:
    """「中２」「小5」などの学年ラベルを school_level と grade_year に変換する。"""
    raw = str(label or "").strip().translate(_FULLWIDTH_DIGITS)
    if not raw or raw.lower() == "nan":
        raise ValueError("学年が空です")
    match = _GRADE_LABEL_RE.match(raw)
    if match is None:
        raise ValueError(f"学年を解析できません: {label}")
    level_char, year_text = match.group(1), match.group(2)
    school_level = _LEVEL_FROM_CHAR[level_char]
    grade_year = int(year_text)
    max_grade = 6 if school_level == "elementary" else 3
    if not 1 <= grade_year <= max_grade:
        raise ValueError(f"学年が範囲外です: {label}")
    return school_level, grade_year


def _student_to_dict(row: StudentProfile) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "school_level": row.school_level,
        "grade_year": row.grade_year,
        "grade_label": grade_label(row.school_level, row.grade_year),
        "level_label": LEVEL_FULL.get(row.school_level, row.school_level),
    }


def _teacher_to_dict(row: TeacherProfile) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "color": row.color,
    }


def _read_json(path) -> dict:
    if not path.is_file():
        return {"items": [], "next_id": 1}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def seed_entities_if_empty() -> None:
    with _session() as db:
        if db.scalar(select(StudentProfile.id).limit(1)) is not None:
            return
        students_raw = _read_json(STUDENTS_PATH)
        for item in students_raw.get("items", []):
            db.add(
                StudentProfile(
                    id=int(item["id"]),
                    name=item["name"],
                    school_level=item.get("school_level", "middle"),
                    grade_year=int(item.get("grade_year", 1)),
                )
            )
        teachers_raw = _read_json(TEACHERS_PATH)
        for item in teachers_raw.get("items", []):
            db.add(
                TeacherProfile(
                    id=int(item["id"]),
                    name=item["name"],
                    color=item.get("color", TEACHER_COLORS[0]),
                )
            )
        db.commit()


def reset_entities_for_tests() -> None:
    from database import Base, engine

    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with _session() as db:
        db.query(StudentProfile).delete()
        db.query(TeacherProfile).delete()
        db.commit()
    seed_entities_if_empty()


def list_students() -> list[dict]:
    with _session() as db:
        rows = db.scalars(select(StudentProfile).order_by(StudentProfile.school_level, StudentProfile.grade_year, StudentProfile.id)).all()
    return deepcopy([_student_to_dict(r) for r in rows])


def list_teachers() -> list[dict]:
    with _session() as db:
        rows = db.scalars(select(TeacherProfile).order_by(TeacherProfile.id)).all()
    return deepcopy([_teacher_to_dict(r) for r in rows])


def find_teacher_by_name(name: str) -> dict | None:
    trimmed = name.strip()
    if not trimmed:
        return None
    with _session() as db:
        row = db.scalars(select(TeacherProfile).where(TeacherProfile.name == trimmed)).first()
    return _teacher_to_dict(row) if row is not None else None


def get_or_create_teacher(name: str) -> tuple[dict, bool]:
    trimmed = name.strip()
    if not trimmed:
        raise HTTPException(status_code=400, detail="講師名が空です")
    existing = find_teacher_by_name(trimmed)
    if existing is not None:
        return existing, False
    return create_teacher(trimmed), True


def find_students_by_name(name: str) -> list[dict]:
    trimmed = name.strip()
    if not trimmed:
        return []
    with _session() as db:
        rows = db.scalars(select(StudentProfile).where(StudentProfile.name == trimmed)).all()
    return deepcopy([_student_to_dict(r) for r in rows])


def get_or_create_student(name: str, grade_label_str: str) -> tuple[dict, bool]:
    trimmed = name.strip()
    if not trimmed:
        raise HTTPException(status_code=400, detail="氏名が空です")
    school_level, grade_year = parse_grade_label(grade_label_str)
    for candidate in find_students_by_name(trimmed):
        if candidate["school_level"] == school_level and candidate["grade_year"] == grade_year:
            return candidate, False
    return create_student(trimmed, school_level, grade_year), True


def get_student(student_id: int) -> dict:
    with _session() as db:
        row = db.get(StudentProfile, student_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Student id={student_id} not found")
    return _student_to_dict(row)


def get_student_name_map() -> dict[int, str]:
    return {s["id"]: s["name"] for s in list_students()}


def _validate_student_fields(school_level: str, grade_year: int) -> None:
    if school_level not in LEVEL_LABELS:
        raise HTTPException(status_code=400, detail="school_level must be elementary, middle, or high")
    max_grade = 6 if school_level == "elementary" else 3
    if not 1 <= grade_year <= max_grade:
        raise HTTPException(status_code=400, detail=f"grade_year must be 1-{max_grade}")


def _sync_student_name(student_id: int, name: str, db: Session) -> None:
    for row in db.scalars(select(AssignmentRow).where(AssignmentRow.student_id == student_id)).all():
        row.student_name = name
    for row in db.scalars(select(AssignmentRequestRow).where(AssignmentRequestRow.student_id == student_id)).all():
        row.student_name = name


def _sync_teacher_name(teacher_id: int, name: str, db: Session) -> None:
    for row in db.scalars(select(AssignmentRow).where(AssignmentRow.teacher_id == teacher_id)).all():
        row.teacher_name = name
    for dash in db.scalars(select(ShiftDashboardRow)).all():
        changed = False
        teachers = []
        for t in dash.teachers:
            if t.get("id") == teacher_id:
                t = {**t, "name": name}
                changed = True
            teachers.append(t)
        if changed:
            dash.teachers = teachers


def create_student(name: str, school_level: str, grade_year: int) -> dict:
    _validate_student_fields(school_level, grade_year)

    with _session() as db:
        row = StudentProfile(name=name, school_level=school_level, grade_year=grade_year)
        db.add(row)
        db.commit()
        db.refresh(row)
        return _student_to_dict(row)


def create_teacher(name: str, color: str | None = None) -> dict:
    with _session() as db:
        count = db.scalar(select(TeacherProfile.id).limit(1))
        existing = db.scalars(select(TeacherProfile)).all()
        picked = color or TEACHER_COLORS[len(existing) % len(TEACHER_COLORS)]
        row = TeacherProfile(name=name, color=picked)
        db.add(row)
        db.commit()
        db.refresh(row)
        return _teacher_to_dict(row)


def update_student(student_id: int, name: str, school_level: str, grade_year: int) -> dict:
    _validate_student_fields(school_level, grade_year)
    with _session() as db:
        row = db.get(StudentProfile, student_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Student id={student_id} not found")
        row.name = name
        row.school_level = school_level
        row.grade_year = grade_year
        _sync_student_name(student_id, name, db)
        db.commit()
        db.refresh(row)
        return _student_to_dict(row)


def delete_student(student_id: int) -> None:
    with _session() as db:
        row = db.get(StudentProfile, student_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Student id={student_id} not found")
        db.query(AssignmentRow).filter(AssignmentRow.student_id == student_id).delete()
        db.query(AssignmentRequestRow).filter(AssignmentRequestRow.student_id == student_id).delete()
        db.query(StudentSubjectPlan).filter(StudentSubjectPlan.student_id == student_id).delete()
        db.query(ShiftSubmission).filter(
            ShiftSubmission.role == "student",
            ShiftSubmission.entity_id == student_id,
        ).delete()
        db.delete(row)
        db.commit()


def update_teacher(teacher_id: int, name: str, color: str | None = None) -> dict:
    with _session() as db:
        row = db.get(TeacherProfile, teacher_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Teacher id={teacher_id} not found")
        row.name = name
        if color:
            row.color = color
        _sync_teacher_name(teacher_id, name, db)
        db.commit()
        db.refresh(row)
        return _teacher_to_dict(row)


def delete_teacher(teacher_id: int) -> None:
    with _session() as db:
        row = db.get(TeacherProfile, teacher_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Teacher id={teacher_id} not found")
        assigned = db.scalar(
            select(AssignmentRow.id).where(AssignmentRow.teacher_id == teacher_id).limit(1)
        )
        if assigned is not None:
            raise HTTPException(status_code=409, detail="割当がある講師は削除できません。先に割当を解除してください。")
        for dash in db.scalars(select(ShiftDashboardRow)).all():
            dash.teachers = [t for t in dash.teachers if t.get("id") != teacher_id]
        db.query(AdminOverride).filter(AdminOverride.teacher_id == teacher_id).delete()
        db.query(ShiftSubmission).filter(
            ShiftSubmission.role == "teacher",
            ShiftSubmission.entity_id == teacher_id,
        ).delete()
        db.delete(row)
        db.commit()


def list_students_grouped() -> list[dict]:
    """小学部/中学部/高校部 → 学年ごとのグループ。"""
    students = list_students()
    groups: dict[tuple[str, int], list] = {}
    for s in students:
        key = (s["school_level"], s["grade_year"])
        groups.setdefault(key, []).append(s)

    order = {"elementary": 0, "middle": 1, "high": 2}
    result = []
    for (level, grade), members in sorted(groups.items(), key=lambda x: (order.get(x[0][0], 9), -x[0][1])):
        result.append(
            {
                "school_level": level,
                "level_label": LEVEL_FULL.get(level, level),
                "grade_year": grade,
                "grade_label": grade_label(level, grade),
                "students": members,
            }
        )
    return result
