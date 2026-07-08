from typing import Any

from fastapi import HTTPException

from services.google_sheets import (
    create_spreadsheet_from_xlsx,
    download_spreadsheet_xlsx,
    parse_spreadsheet_id,
    upload_spreadsheet_xlsx,
)
from services.juku_grid_export import export_juku_schedule_workbook
from services.juku_grid_import import import_juku_grid_workbook, import_juku_grid_xlsx
from services.period_store import get_period


def import_from_google_sheet(
    period_id: int,
    spreadsheet_ref: str,
    *,
    iso_date: str | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    period = get_period(period_id)
    if period.status not in ("DRAFT", "COLLECTING"):
        raise HTTPException(status_code=409, detail="取り込みは DRAFT または COLLECTING の講習期間のみ可能です")

    spreadsheet_id = parse_spreadsheet_id(spreadsheet_ref)
    raw = download_spreadsheet_xlsx(spreadsheet_id)
    filename = f"google_{spreadsheet_id[:8]}.xlsx"

    if iso_date:
        stats = import_juku_grid_xlsx(period_id, raw, iso_date, sheet_name, filename=filename)
        stats["spreadsheet_id"] = spreadsheet_id
        stats["message"] = (
            f"{stats['rows_processed']} 件を取り込みました"
            f"（{stats['resolved_date']} / リクエスト +{stats['requests_added']}）"
        )
        return stats

    stats = import_juku_grid_workbook(period_id, raw, filename)
    stats["spreadsheet_id"] = spreadsheet_id
    sheets = stats.get("imported_sheets") or []
    stats["message"] = (
        f"{stats['imported_sheet_count']} シート・{stats['rows_processed']} 件を取り込みました"
        f"（{', '.join(sheets[:5])}{'…' if len(sheets) > 5 else ''}）"
    )
    return stats


def import_all_daily_sheets_from_xlsx(
    period_id: int,
    raw: bytes,
    spreadsheet_id: str = "",
) -> dict[str, Any]:
    """後方互換。月次一括取込に委譲。"""
    filename = f"google_{spreadsheet_id[:8]}.xlsx" if spreadsheet_id else "google_import.xlsx"
    stats = import_juku_grid_workbook(period_id, raw, filename)
    stats["spreadsheet_id"] = spreadsheet_id
    stats["imported_sheet_count"] = stats.get("imported_sheet_count", 0)
    stats["skipped_sheets"] = []
    stats["dates"] = stats.get("resolved_dates") or []
    stats["sheets"] = stats.get("imported_sheets") or []
    stats["message"] = (
        f"{stats['imported_sheet_count']} シートを取り込みました（{stats['rows_processed']} 行 / "
        f"リクエスト +{stats['requests_added']}）"
    )
    return stats


def export_to_google_sheet(
    period_id: int,
    spreadsheet_ref: str | None = None,
    *,
    title: str | None = None,
) -> dict[str, str]:
    period = get_period(period_id)
    content = export_juku_schedule_workbook(period_id, period.location_slug)

    if spreadsheet_ref:
        spreadsheet_id = parse_spreadsheet_id(spreadsheet_ref)
        upload_spreadsheet_xlsx(spreadsheet_id, content)
        return {
            "spreadsheet_id": spreadsheet_id,
            "web_view_link": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
            "message": f"講習「{period.name}」の確定時間割を Google スプレッドシートに書き込みました",
        }

    file_title = title or f"{period.name}_確定時間割"
    created = create_spreadsheet_from_xlsx(file_title, content)
    return {
        **created,
        "message": f"新しいスプレッドシート「{file_title}」を作成しました",
    }
