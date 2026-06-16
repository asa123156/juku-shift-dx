"""pandas で時間割 CSV を読み込み、講師・生徒マスタと固定枠へ反映する。"""

from __future__ import annotations

import io
import re
from datetime import date, datetime

import pandas as pd
from fastapi import HTTPException

from services.entity_store import get_or_create_student, get_or_create_teacher
from services.period_store import get_period, iter_dates, set_period_base_slot
from services.slot_timing import SLOT_COUNT, SLOT_KEYS

_REQUIRED_COLUMNS = {"teacher_name", "grade", "subject", "lesson_type", "slot_date", "slot_key", "student_name"}

_COLUMN_ALIASES: dict[str, str] = {
    "講師名": "teacher_name",
    "teacher_name": "teacher_name",
    "teacher": "teacher_name",
    "氏名": "student_name",
    "生徒名": "student_name",
    "student_name": "student_name",
    "name": "student_name",
    "学年": "grade",
    "grade": "grade",
    "科目": "subject",
    "subject": "subject",
    "種別": "lesson_type",
    "type": "lesson_type",
    "lesson_type": "lesson_type",
    "日付": "slot_date",
    "date": "slot_date",
    "コマ": "slot_key",
    "slot": "slot_key",
}

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _normalize_header(name: str) -> str | None:
    key = str(name or "").strip()
    if not key:
        return None
    return _COLUMN_ALIASES.get(key) or _COLUMN_ALIASES.get(key.lower())


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename: dict[str, str] = {}
    for col in df.columns:
        canonical = _normalize_header(col)
        if canonical:
            rename[col] = canonical
    if not rename:
        return df
    return df.rename(columns=rename)


def _cell_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _parse_iso_date(value: object, line_no: int) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        raise HTTPException(status_code=400, detail=f"{line_no} 行目: 日付が空です")
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    text = _cell_text(value)
    if _DATE_PATTERN.match(text):
        return text
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        raise HTTPException(
            status_code=400,
            detail=f"{line_no} 行目: 日付は YYYY-MM-DD 形式で指定してください",
        )
    return parsed.strftime("%Y-%m-%d")


def _parse_slot_key(value: object, line_no: int) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        raise HTTPException(status_code=400, detail=f"{line_no} 行目: コマが空です")
    if isinstance(value, float):
        value = int(value)
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if text not in SLOT_KEYS:
        raise HTTPException(
            status_code=400,
            detail=f"{line_no} 行目: コマは 1-{SLOT_COUNT} で指定してください",
        )
    return text


def _symbol_from_lesson_type(lesson_type: str) -> str:
    if "講習" in lesson_type:
        return ""
    return "◎"


def read_schedule_dataframe(content: str) -> pd.DataFrame:
    if not content.strip():
        raise HTTPException(status_code=400, detail="CSV が空です")
    try:
        df = pd.read_csv(io.StringIO(content), dtype=str, keep_default_na=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="CSV を読み込めません") from exc
    if df.empty:
        raise HTTPException(status_code=400, detail="取り込めるデータ行がありません")
    return _normalize_columns(df)


def _validate_columns(df: pd.DataFrame) -> None:
    missing = sorted(_REQUIRED_COLUMNS - set(df.columns))
    if missing:
        labels = {
            "teacher_name": "講師名",
            "grade": "学年",
            "subject": "科目",
            "lesson_type": "種別",
            "slot_date": "日付",
            "slot_key": "コマ",
            "student_name": "氏名",
        }
        missing_ja = ", ".join(labels.get(col, col) for col in missing)
        raise HTTPException(status_code=400, detail=f"必須列が不足しています: {missing_ja}")


def import_schedule_csv(period_id: int, content: str) -> dict[str, int]:
    period = get_period(period_id)
    if period.status not in ("DRAFT", "COLLECTING"):
        raise HTTPException(status_code=409, detail="取り込みは DRAFT または COLLECTING の講習期間のみ可能です")

    df = read_schedule_dataframe(content)
    _validate_columns(df)

    allowed_dates = set(iter_dates(period.start_date, period.end_date))
    stats = {
        "rows_processed": 0,
        "teachers_created": 0,
        "students_created": 0,
        "teacher_slots_saved": 0,
        "student_slots_saved": 0,
        "blank_slots": 0,
        "regular_slots": 0,
    }

    for idx, row in df.iterrows():
        line_no = int(idx) + 2
        teacher_name = _cell_text(row.get("teacher_name"))
        student_name = _cell_text(row.get("student_name"))
        grade = _cell_text(row.get("grade"))
        subject = _cell_text(row.get("subject"))
        lesson_type = _cell_text(row.get("lesson_type"))

        if not any([teacher_name, student_name, grade, subject, lesson_type]):
            continue
        if not teacher_name:
            raise HTTPException(status_code=400, detail=f"{line_no} 行目: 講師名が空です")
        if not student_name:
            raise HTTPException(status_code=400, detail=f"{line_no} 行目: 氏名が空です")
        if not grade:
            raise HTTPException(status_code=400, detail=f"{line_no} 行目: 学年が空です")
        if not subject:
            raise HTTPException(status_code=400, detail=f"{line_no} 行目: 科目が空です")
        if not lesson_type:
            raise HTTPException(status_code=400, detail=f"{line_no} 行目: 種別が空です")

        iso_date = _parse_iso_date(row.get("slot_date"), line_no)
        if iso_date not in allowed_dates:
            raise HTTPException(status_code=400, detail=f"{line_no} 行目: 日付が講習期間外です")
        slot_key = _parse_slot_key(row.get("slot_key"), line_no)
        symbol = _symbol_from_lesson_type(lesson_type)

        teacher, teacher_created = get_or_create_teacher(teacher_name)
        if teacher_created:
            stats["teachers_created"] += 1

        try:
            student, student_created = get_or_create_student(student_name, grade)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"{line_no} 行目: {exc}") from exc
        if student_created:
            stats["students_created"] += 1

        set_period_base_slot(period_id, "teacher", teacher["id"], iso_date, slot_key, symbol)
        set_period_base_slot(period_id, "student", student["id"], iso_date, slot_key, symbol)
        stats["rows_processed"] += 1
        stats["teacher_slots_saved"] += 1
        stats["student_slots_saved"] += 1
        if symbol == "":
            stats["blank_slots"] += 1
        else:
            stats["regular_slots"] += 1

    if stats["rows_processed"] == 0:
        raise HTTPException(status_code=400, detail="取り込めるデータ行がありません")

    return stats
