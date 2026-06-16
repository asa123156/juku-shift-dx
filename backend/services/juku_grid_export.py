"""インポート済み月次 Excel に確定割当を書き込んで返す。"""

from __future__ import annotations

import io

from fastapi import HTTPException
from openpyxl import load_workbook

from services.assignment_store import get_assignments_for_date
from services.entity_store import get_student
from services.juku_grid_parser import (
    list_schedule_sheet_names,
    load_grid_map,
    resolve_dates_for_sheet,
)
from services.period_store import get_period
from services.schedule_workbook_store import get_period_workbook
from services.slot_timing import generate_time_slots

# テンプレート書き出し用（Google 連携などで旧来 API が必要な場合のみ）
from datetime import date, datetime, time  # noqa: E402
from pathlib import Path  # noqa: E402
import re  # noqa: E402

from config import BACKEND_DIR  # noqa: E402

TEMPLATES_DIR = BACKEND_DIR / "templates"


def _slot_to_time(slot: int) -> time:
    for item in generate_time_slots():
        if item["slot"] == slot:
            hh, mm = item["start"].split(":")
            return time(int(hh), int(mm))
    raise HTTPException(status_code=400, detail=f"不明なコマ: {slot}")


def _count_names_in_row(ws, row_idx: int) -> int:
    return sum(1 for col in range(1, ws.max_column + 1) if ws.cell(row=row_idx, column=col).value == "氏名")


def _find_header_row_for_slot(ws, slot: int) -> int | None:
    cfg = load_grid_map()
    time_col = cfg["time_column"] + 1
    target_time = _slot_to_time(slot)

    for row_idx in range(1, ws.max_row + 1):
        cell_val = ws.cell(row=row_idx, column=time_col).value
        if not isinstance(cell_val, time):
            continue
        if cell_val.hour != target_time.hour or cell_val.minute != target_time.minute:
            continue
        if _count_names_in_row(ws, row_idx) >= 2:
            return row_idx
        if row_idx + 1 <= ws.max_row and _count_names_in_row(ws, row_idx + 1) >= 2:
            return row_idx + 1

    return None


def _data_row_range(ws, header_row: int, slot: int) -> range:
    cfg = load_grid_map()
    time_col = cfg["time_column"] + 1
    target_time = _slot_to_time(slot)
    end_row = ws.max_row
    for row_idx in range(header_row + 1, ws.max_row + 1):
        val = ws.cell(row=row_idx, column=time_col).value
        if isinstance(val, time) and not (val.hour == target_time.hour and val.minute == target_time.minute):
            end_row = row_idx - 1
            break
        if _count_names_in_row(ws, row_idx) >= 2 and row_idx != header_row:
            end_row = row_idx - 1
            break
    return range(header_row + 1, end_row + 1)


def _teacher_col_index(teacher_columns: list[int], slot: int, teacher_id: int, assignments: list[dict]) -> int:
    teacher_ids = sorted({a["teacher_id"] for a in assignments if a["slot"] == slot})
    if teacher_id not in teacher_ids:
        return teacher_columns[0]
    idx = teacher_ids.index(teacher_id)
    if idx >= len(teacher_columns):
        idx = len(teacher_columns) - 1
    return teacher_columns[idx]


def _set_date_header(ws, iso_date: str) -> None:
    cfg = load_grid_map()
    dr, dc = cfg["date_header_row"], cfg["date_header_col"]
    ws.cell(row=dr + 1, column=dc + 1, value=datetime.combine(date.fromisoformat(iso_date), time.min))


def _fill_assignments_on_sheet(ws, iso_date: str, assignments: list[dict]) -> None:
    cfg = load_grid_map()
    teacher_columns: list[int] = cfg["teacher_columns"]
    offsets = cfg["offsets_from_teacher"]

    if not assignments:
        return

    fill_counts: dict[tuple[int, int], int] = {}
    for assign in sorted(assignments, key=lambda x: (x["slot"], x["teacher_id"], x["student_id"])):
        slot = int(assign["slot"])
        header_row = _find_header_row_for_slot(ws, slot)
        if header_row is None:
            continue
        teacher_col = _teacher_col_index(teacher_columns, slot, assign["teacher_id"], assignments)
        tc = teacher_col + 1

        count_key = (slot, assign["teacher_id"])
        fill_idx = fill_counts.get(count_key, 0)
        fill_counts[count_key] = fill_idx + 1

        use_b = fill_idx % 2 == 1
        name_key = "name_b" if use_b else "name_a"
        subject_key = "subject_b" if use_b else "subject_a"
        grade_key = "grade_b" if use_b else "grade_a"

        data_rows = list(_data_row_range(ws, header_row, slot))
        if not data_rows:
            continue
        target_row = data_rows[min(fill_idx // 2, len(data_rows) - 1)]

        name_col = tc + offsets[name_key]
        subject_col = tc + offsets[subject_key]
        grade_col = tc + offsets[grade_key]
        teacher_cell_col = tc + offsets["teacher"]

        try:
            student = get_student(assign["student_id"])
            g_label = student["grade_label"]
        except HTTPException:
            g_label = ""

        ws.cell(row=target_row, column=name_col, value=assign["student_name"])
        ws.cell(row=target_row, column=subject_col, value=assign["subject"])
        if g_label:
            ws.cell(row=target_row, column=name_col - 1, value=g_label)
            ws.cell(row=target_row, column=grade_col, value=g_label)
        ws.cell(row=target_row, column=teacher_cell_col, value=assign["teacher_name"])


def _workbook_bytes(wb) -> bytes:
    out = io.BytesIO()
    wb.save(out)
    wb.close()
    return out.getvalue()


def export_period_schedule_workbook(period_id: int) -> tuple[bytes, str]:
    """インポート済み月次 Excel に割当を反映して返す（非時間割シートは変更しない）。"""
    stored = get_period_workbook(period_id)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="月次時間割 Excel が未インポートです。先にデータインポートから取り込んでください",
        )

    raw, filename = stored
    period = get_period(period_id)
    period_year = int(str(period.start_date)[:4])
    cfg = load_grid_map()

    wb = load_workbook(io.BytesIO(raw))
    schedule_sheets = list_schedule_sheet_names(raw)

    for sheet_name in schedule_sheets:
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        dates = resolve_dates_for_sheet(sheet_name, rows, period_year, cfg)
        if not dates:
            continue
        for iso_date in dates:
            assignments = get_assignments_for_date(iso_date)
            if assignments:
                _fill_assignments_on_sheet(ws, iso_date, assignments)

    return _workbook_bytes(wb), filename


def _template_path() -> Path:
    cfg = load_grid_map()
    path = TEMPLATES_DIR / cfg["template_file"]
    if not path.is_file():
        raise HTTPException(status_code=500, detail="時間割テンプレートが見つかりません")
    return path


def _daily_template_sheet_name(wb) -> str:
    daily = [s for s in wb.sheetnames if re.match(r"\d+月\d+日", s)]
    if not daily:
        raise HTTPException(status_code=500, detail="日次シートがテンプレートにありません")
    return daily[0]


def _sheet_title_for_date(iso_date: str) -> str:
    d = date.fromisoformat(iso_date)
    return f"{d.month}月{d.day}日"


def _build_workbook_from_template(period_id: int) -> bytes:
    """インポートファイルが無い場合の Google 書き出し用フォールバック。"""
    from services.period_store import open_dates_for_period

    period = get_period(period_id)
    if period.status != "FINALIZED":
        raise HTTPException(status_code=409, detail="エクスポートは FINALIZED の講習期間のみ可能です")

    open_dates = open_dates_for_period(period)
    if not open_dates:
        raise HTTPException(status_code=404, detail="開校日がありません")

    template_bytes = _template_path().read_bytes()
    wb = load_workbook(io.BytesIO(template_bytes))
    template_name = _daily_template_sheet_name(wb)
    for name in list(wb.sheetnames):
        if name != template_name:
            del wb[name]

    for idx, iso_date in enumerate(open_dates):
        if idx == 0:
            ws = wb[template_name]
        else:
            fresh = load_workbook(io.BytesIO(template_bytes))
            fresh_name = _daily_template_sheet_name(fresh)
            ws = wb.copy_worksheet(fresh[fresh_name])
            fresh.close()
        ws.title = _sheet_title_for_date(iso_date)[:31]
        assignments = get_assignments_for_date(iso_date)
        _set_date_header(ws, iso_date)
        _fill_assignments_on_sheet(ws, iso_date, assignments)

    return _workbook_bytes(wb)


def export_juku_schedule_workbook(period_id: int) -> bytes:
    """Google 書き込み用。インポート済みファイルがあればそれを、なければテンプレートから生成。"""
    stored = get_period_workbook(period_id)
    if stored is not None:
        content, _ = export_period_schedule_workbook(period_id)
        return content
    return _build_workbook_from_template(period_id)
