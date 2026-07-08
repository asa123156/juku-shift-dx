"""縦持ちレコードを DB（固定枠・割当リクエスト）へ反映する。"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from services.assignment_store import append_assignment_requests, get_assignments_for_date
from services.class_schedule_store import save_schedules_for_date
from services.entity_store import get_or_create_student, get_or_create_teacher
from services.period_store import get_period, iter_dates
from services.schedule_csv_import import _symbol_from_lesson_type


def import_juku_grid_records(period_id: int, records: list[dict[str, Any]]) -> dict[str, int]:
    period = get_period(period_id)
    if period.status not in ("DRAFT", "COLLECTING"):
        raise HTTPException(status_code=409, detail="取り込みは DRAFT または COLLECTING の講習期間のみ可能です")

    allowed_dates = set(iter_dates(period.start_date, period.end_date))
    stats = {
        "rows_processed": 0,
        "teachers_created": 0,
        "students_created": 0,
        "teacher_slots_saved": 0,
        "student_slots_saved": 0,
        "blank_slots": 0,
        "regular_slots": 0,
        "requests_added": 0,
        "requests_skipped": 0,
    }
    seen_slot_pairs: set[tuple[str, str, int, str, str]] = set()
    requests_by_date: dict[str, list[dict]] = {}
    regular_assignments_by_date: dict[str, list[dict]] = {}
    new_teacher_ids: set[int] = set()

    for rec in records:
        iso_date = rec["date"]
        if iso_date not in allowed_dates:
            raise HTTPException(
                status_code=400,
                detail=f"日付 {iso_date} が講習期間外です（行 {rec.get('row_idx', '?')}）",
            )

        student_name = rec.get("student_name", "").strip()
        teacher_name = rec.get("teacher_name", "").strip()
        grade = rec.get("grade", "").strip()
        subject = rec.get("subject", "").strip()
        lesson_type = rec.get("lesson_type", "").strip()
        slot_key = str(rec.get("slot_key", ""))

        if not student_name:
            continue

        if not grade:
            raise HTTPException(
                status_code=400,
                detail=f"{student_name} の学年が空です（行 {rec.get('row_idx', '?')}）",
            )

        try:
            student, student_created = get_or_create_student(student_name, grade)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"行 {rec.get('row_idx', '?')}: {exc}",
            ) from exc
        if student_created:
            stats["students_created"] += 1

        teacher = None
        if teacher_name:
            teacher, teacher_created = get_or_create_teacher(teacher_name)
            if teacher_created:
                stats["teachers_created"] += 1
                new_teacher_ids.add(teacher["id"])

        symbol = _symbol_from_lesson_type(lesson_type)
        is_regular_lesson = symbol == "◎"
        if symbol == "":
            stats["blank_slots"] += 1

        if teacher is not None and slot_key and is_regular_lesson:
            regular_assignments_by_date.setdefault(iso_date, []).append(
                {
                    "date": iso_date,
                    "student_id": student["id"],
                    "student_name": student["name"],
                    "subject": subject,
                    "teacher_id": teacher["id"],
                    "teacher_name": teacher["name"],
                    "slot": int(slot_key),
                    "is_fixed": True,
                    "source": "excel",
                }
            )
            stats["regular_slots"] += 1
        elif subject:
            requests_by_date.setdefault(iso_date, []).append(
                {
                    "student_id": student["id"],
                    "student_name": student["name"],
                    "subject": subject,
                }
            )

        stats["rows_processed"] += 1

    for iso_date, regular_assignments in regular_assignments_by_date.items():
        existing = get_assignments_for_date(iso_date)
        tutoring = [a for a in existing if not a.get("is_fixed") and (a.get("lesson_kind") or "講習") != "通常"]
        merged = tutoring + regular_assignments
        deduped: list[dict] = []
        seen: set[tuple[int, int, int, str, bool]] = set()
        for row in merged:
            fixed = bool(row.get("is_fixed") or row.get("lesson_kind") == "通常")
            key = (
                int(row["student_id"]),
                int(row["teacher_id"]),
                int(row["slot"]),
                str(row["subject"]),
                fixed,
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        save_schedules_for_date(iso_date, deduped, period_id=period_id)
        stats["teacher_slots_saved"] += len(regular_assignments)
        stats["student_slots_saved"] += len(regular_assignments)

    for iso_date, reqs in requests_by_date.items():
        added, skipped = append_assignment_requests(iso_date, reqs)
        stats["requests_added"] += added
        stats["requests_skipped"] += skipped

    if new_teacher_ids:
        from services.period_bootstrap import add_teachers_to_period_dashboards

        stats["dashboard_teachers_added"] = add_teachers_to_period_dashboards(
            period_id, sorted(new_teacher_ids)
        )
    else:
        stats["dashboard_teachers_added"] = 0

    if stats["rows_processed"] == 0:
        raise HTTPException(status_code=400, detail="取り込めるデータ行がありません")

    return stats


def import_juku_grid_xlsx(
    period_id: int,
    raw: bytes,
    iso_date: str,
    sheet_name: str | None = None,
    *,
    filename: str | None = None,
    save_workbook: bool = True,
) -> dict[str, Any]:
    from services.juku_grid_parser import read_workbook_sheet
    from services.schedule_workbook_store import save_period_workbook

    if save_workbook:
        save_period_workbook(period_id, filename or "schedule.xlsx", raw)

    period = get_period(period_id)
    period_year = int(str(period.start_date)[:4])
    records, sheet = read_workbook_sheet(raw, iso_date, period_year, sheet_name)
    stats = import_juku_grid_records(period_id, records)
    stats["parsed_rows"] = len(records)
    stats["resolved_date"] = records[0]["date"] if records else iso_date
    stats["sheet_name"] = sheet
    stats["imported_sheets"] = [sheet]
    stats["imported_sheet_count"] = 1
    stats["workbook_filename"] = filename
    return stats


def import_juku_grid_workbook(
    period_id: int,
    raw: bytes,
    filename: str,
) -> dict[str, Any]:
    """月次 Excel を保存し、時間割シートのみ一括取り込む。"""
    from services.juku_grid_parser import list_schedule_sheet_names, parse_sheet_records
    from services.schedule_workbook_store import save_period_workbook

    save_period_workbook(period_id, filename, raw)

    sheet_names = list_schedule_sheet_names(raw)
    if not sheet_names:
        raise HTTPException(
            status_code=400,
            detail="時間割シートが見つかりません（参照・講師シフト以外にグリッド形式のシートが必要です）",
        )

    period = get_period(period_id)
    period_year = int(str(period.start_date)[:4])
    all_records: list[dict[str, Any]] = []
    for sheet_name in sheet_names:
        all_records.extend(parse_sheet_records(raw, sheet_name, period_year))

    stats = import_juku_grid_records(period_id, all_records)
    stats["parsed_rows"] = len(all_records)
    stats["imported_sheets"] = sheet_names
    stats["imported_sheet_count"] = len(sheet_names)
    stats["workbook_filename"] = filename
    resolved_dates = sorted({r["date"] for r in all_records})
    stats["resolved_date"] = resolved_dates[0] if resolved_dates else None
    stats["resolved_dates"] = resolved_dates
    stats["sheet_name"] = sheet_names[0] if len(sheet_names) == 1 else None
    return stats
