"""生徒・講師マスタの CRUD と学年ラベル。"""

import json
import re
import secrets
from copy import deepcopy

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import DATA_DIR
from database import SessionLocal
from security import hash_password
from models import AdminOverride, Assignment as AssignmentRow
from models import AssignmentRequest as AssignmentRequestRow
from models import ClassSchedule as ClassScheduleRow
from models import ShiftDashboard as ShiftDashboardRow
from models import ShiftSubmission
from models import StudentProfile, TeacherProfile
from models import StudentSubjectPlan

STUDENTS_PATH = DATA_DIR / "students.json"
TEACHERS_PATH = DATA_DIR / "teachers.json"
USERS_PATH = DATA_DIR / "users.json"

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
    creds = _credentials_for_entity("student", row.id)
    return {
        "id": row.id,
        "name": row.name,
        "school_level": row.school_level,
        "grade_year": row.grade_year,
        "grade_label": grade_label(row.school_level, row.grade_year),
        "level_label": LEVEL_FULL.get(row.school_level, row.school_level),
        "login_id": creds["login_id"],
        "password": creds["password"],
    }


def _teacher_to_dict(row: TeacherProfile) -> dict:
    creds = _credentials_for_entity("teacher", row.id)
    return {
        "id": row.id,
        "name": row.name,
        "color": row.color,
        "login_id": creds["login_id"],
        "password": creds["password"],
    }


def _read_json(path) -> dict:
    if not path.is_file():
        return {"items": [], "next_id": 1}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _load_users() -> list[dict]:
    if not USERS_PATH.is_file():
        return []
    with USERS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _save_users(users: list[dict]) -> None:
    USERS_PATH.write_text(
        json.dumps(users, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _credential_keys(role: str) -> tuple[str, str]:
    if role == "student":
        return "student_id", "/student-schedule"
    return "teacher_id", "/teacher"


def _default_login(role: str, entity_id: int) -> str:
    prefix = "student" if role == "student" else "teacher"
    return f"{prefix}{entity_id}@example.com"


def _default_password(role: str, entity_id: int) -> str:
    prefix = "std" if role == "student" else "tch"
    return f"{prefix}-{entity_id:03d}-{secrets.token_hex(2)}"


def _find_user_for_entity(users: list[dict], role: str, entity_id: int) -> dict | None:
    id_key, _ = _credential_keys(role)
    for user in users:
        if user.get("role") == role and user.get(id_key) == entity_id:
            return user
    return None


def _upsert_entity_user(
    role: str, entity_id: int, name: str, *, force_new_password: bool = False
) -> dict[str, str]:
    """users.json にはハッシュのみ保存する。平文パスワードは発行直後だけ呼び出し元に返す。"""
    users = _load_users()
    id_key, redirect = _credential_keys(role)
    existing = _find_user_for_entity(users, role, entity_id)
    if existing is not None:
        existing["name"] = name
        existing["redirect"] = redirect
        if not existing.get("email"):
            existing["email"] = _default_login(role, entity_id)
        new_password = ""
        if force_new_password or not existing.get("password"):
            new_password = _default_password(role, entity_id)
            existing["password"] = hash_password(new_password)
        _save_users(users)
        return {"login_id": existing["email"], "password": new_password}

    taken = {str(u.get("email", "")).lower() for u in users}
    email = _default_login(role, entity_id)
    if email.lower() in taken:
        local, domain = email.split("@", 1)
        suffix = 2
        while f"{local}{suffix}@{domain}".lower() in taken:
            suffix += 1
        email = f"{local}{suffix}@{domain}"

    password = _default_password(role, entity_id)
    user = {
        "email": email,
        "password": hash_password(password),
        "role": role,
        "teacher_id": None,
        "student_id": None,
        "name": name,
        "redirect": redirect,
    }
    user[id_key] = entity_id
    users.append(user)
    _save_users(users)
    return {"login_id": email, "password": password}


def _remove_entity_user(role: str, entity_id: int) -> None:
    users = _load_users()
    id_key, _ = _credential_keys(role)
    filtered = [
        u for u in users
        if not (u.get("role") == role and u.get(id_key) == entity_id)
    ]
    if len(filtered) != len(users):
        _save_users(filtered)


def _credentials_for_entity(role: str, entity_id: int) -> dict[str, str]:
    """一覧表示用。password は常に空文字（ハッシュは表示しない）。"""
    user = _find_user_for_entity(_load_users(), role, entity_id)
    if user is None:
        return {"login_id": "", "password": ""}
    return {
        "login_id": str(user.get("email", "")),
        "password": "",
    }


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
    for student in list_students():
        _upsert_entity_user("student", int(student["id"]), str(student["name"]))
    for teacher in list_teachers():
        _upsert_entity_user("teacher", int(teacher["id"]), str(teacher["name"]))


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
    for row in db.scalars(select(ClassScheduleRow).where(ClassScheduleRow.student_id == student_id)).all():
        row.student_name = name
    for row in db.scalars(select(AssignmentRow).where(AssignmentRow.student_id == student_id)).all():
        row.student_name = name
    for row in db.scalars(select(AssignmentRequestRow).where(AssignmentRequestRow.student_id == student_id)).all():
        row.student_name = name


def _sync_teacher_name(teacher_id: int, name: str, db: Session) -> None:
    for row in db.scalars(select(ClassScheduleRow).where(ClassScheduleRow.teacher_id == teacher_id)).all():
        row.teacher_name = name
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
        creds = _upsert_entity_user("student", row.id, row.name)
        result = _student_to_dict(row)
        result["password"] = creds["password"]
        return result


def change_user_password(email: str, current_password: str, new_password: str) -> None:
    """本人によるパスワード変更。現パスワードの検証に失敗したら 403。"""
    from security import verify_password

    users = _load_users()
    user = next((u for u in users if u.get("email", "").lower() == email.lower()), None)
    if user is None:
        raise HTTPException(status_code=404, detail="アカウントが見つかりません")
    if not verify_password(current_password, user.get("password", "")):
        raise HTTPException(status_code=403, detail="現在のパスワードが正しくありません")
    user["password"] = hash_password(new_password)
    _save_users(users)


def reset_student_password(student_id: int) -> dict:
    with _session() as db:
        row = db.get(StudentProfile, student_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Student id={student_id} not found")
        creds = _upsert_entity_user("student", row.id, row.name, force_new_password=True)
        result = _student_to_dict(row)
        result["password"] = creds["password"]
        return result


def create_teacher(name: str, color: str | None = None) -> dict:
    with _session() as db:
        existing = db.scalars(select(TeacherProfile)).all()
        picked = color or TEACHER_COLORS[len(existing) % len(TEACHER_COLORS)]
        row = TeacherProfile(name=name, color=picked)
        db.add(row)
        db.commit()
        db.refresh(row)
        creds = _upsert_entity_user("teacher", row.id, row.name)
        teacher = _teacher_to_dict(row)
        teacher["password"] = creds["password"]
    from services.period_bootstrap import sync_teacher_to_all_period_dashboards

    sync_teacher_to_all_period_dashboards(teacher["id"])
    return teacher


def reset_teacher_password(teacher_id: int) -> dict:
    with _session() as db:
        row = db.get(TeacherProfile, teacher_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Teacher id={teacher_id} not found")
        creds = _upsert_entity_user("teacher", row.id, row.name, force_new_password=True)
        result = _teacher_to_dict(row)
        result["password"] = creds["password"]
        return result


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
        _upsert_entity_user("student", row.id, row.name)
        return _student_to_dict(row)


def delete_student(student_id: int) -> None:
    with _session() as db:
        row = db.get(StudentProfile, student_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Student id={student_id} not found")
        db.query(ClassScheduleRow).filter(ClassScheduleRow.student_id == student_id).delete()
        db.query(AssignmentRow).filter(AssignmentRow.student_id == student_id).delete()
        db.query(AssignmentRequestRow).filter(AssignmentRequestRow.student_id == student_id).delete()
        db.query(StudentSubjectPlan).filter(StudentSubjectPlan.student_id == student_id).delete()
        db.query(ShiftSubmission).filter(
            ShiftSubmission.role == "student",
            ShiftSubmission.entity_id == student_id,
        ).delete()
        db.delete(row)
        db.commit()
    _remove_entity_user("student", student_id)


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
        _upsert_entity_user("teacher", row.id, row.name)
        return _teacher_to_dict(row)


def delete_teacher(teacher_id: int) -> None:
    with _session() as db:
        row = db.get(TeacherProfile, teacher_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Teacher id={teacher_id} not found")
        assigned = db.scalar(
            select(ClassScheduleRow.id).where(ClassScheduleRow.teacher_id == teacher_id).limit(1)
        )
        if assigned is None:
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
    _remove_entity_user("teacher", teacher_id)


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
