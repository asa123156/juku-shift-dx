"""白庭台グリッドのパーサー・インポート・エクスポートテスト。"""

import io
from datetime import time
from pathlib import Path

from openpyxl import Workbook

from services.juku_grid_import import import_juku_grid_records
from services.juku_grid_parser import list_schedule_sheet_names, load_grid_map, parse_juku_grid_xlsx


def _build_minimal_grid_xlsx() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "6月11日"
    ws["B1"] = "2026-06-11"
    row = 5
    ws.cell(row=row, column=1, value=time(13, 0))
    ws.cell(row=row, column=2, value="座席")
    ws.cell(row=row, column=3, value="学年")
    ws.cell(row=row, column=5, value="氏名")
    ws.cell(row=row, column=6, value="科目")
    ws.cell(row=row, column=7, value="種別(通常はブランク)")
    ws.cell(row=row, column=10, value="講師")
    ws.cell(row=row, column=11, value="学年")
    ws.cell(row=row, column=13, value="氏名")
    ws.cell(row=row, column=14, value="科目")
    ws.cell(row=row, column=15, value="種別(通常はブランク)")
    data = 6
    ws.cell(row=data, column=2, value=1)
    ws.cell(row=data, column=4, value="中2")
    ws.cell(row=data, column=5, value="グリッド太郎")
    ws.cell(row=data, column=6, value="数学")
    ws.cell(row=data, column=10, value="グリッド講師")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_hakutei_template() -> None:
    template = (
        Path(__file__).resolve().parents[1] / "locations" / "hakutei" / "schedule_template.xlsx"
    )
    records = parse_juku_grid_xlsx(template.read_bytes(), "2026-06-29", 2026, "6月29日")
    assert records == []


def test_list_schedule_sheets_skips_reference() -> None:
    import io
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "参照シート"
    ws["A1"] = "参照データ"
    grid = wb.create_sheet("6月11日")
    grid["B1"] = "2026-06-11"
    row = 5
    grid.cell(row=row, column=1, value=time(13, 0))
    grid.cell(row=row, column=5, value="氏名")
    grid.cell(row=row, column=13, value="氏名")
    buf = io.BytesIO()
    wb.save(buf)
    names = list_schedule_sheet_names(buf.getvalue())
    assert names == ["6月11日"]


def test_parse_minimal_grid() -> None:
    records = parse_juku_grid_xlsx(_build_minimal_grid_xlsx(), "2026-06-11", 2026)
    assert len(records) == 1
    assert records[0]["student_name"] == "グリッド太郎"
    assert records[0]["slot_key"] == "1"
    assert records[0]["date"] == "2026-06-11"


def test_import_records() -> None:
    from scripts.generate_demo_data import main as generate_demo
    from services.assignment_store import get_assignments_for_date
    from services.entity_store import reset_entities_for_tests
    from services.period_store import reset_periods_for_tests

    generate_demo()
    reset_periods_for_tests()
    reset_entities_for_tests()

    records = [
        {
            "date": "2026-06-11",
            "slot_key": "1",
            "student_name": "グリッド花子",
            "grade": "小4",
            "subject": "国語",
            "lesson_type": "",
            "teacher_name": "グリッド先生",
            "row_idx": 6,
        }
    ]
    stats = import_juku_grid_records(1, records)
    assert stats["rows_processed"] == 1
    assert stats["teachers_created"] >= 1
    assert stats["requests_added"] == 0
    assignments = get_assignments_for_date("2026-06-11")
    assert any(
        a["student_name"] == "グリッド花子"
        and a["teacher_name"] == "グリッド先生"
        and a.get("is_fixed") is True
        and a.get("lesson_kind") == "通常"
        for a in assignments
    )


def run_tests() -> None:
    test_parse_hakutei_template()
    test_list_schedule_sheets_skips_reference()
    test_parse_minimal_grid()
    test_import_records()
    print("juku grid tests passed.")


if __name__ == "__main__":
    run_tests()
