import csv
import io
import re

from fastapi import HTTPException

from services.assignment_store import append_assignment_requests

_REQUIRED_COLUMNS = {"date", "student_id", "student_name", "subject"}
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _normalize_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def parse_assignment_requests_csv(content: str) -> list[dict]:
    """
    CSV 形式:
    date,student_id,student_name,subject
    2026-06-11,1,近大太郎,数学I
    """
    if not content.strip():
        raise HTTPException(status_code=400, detail="CSV が空です")

    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="CSV にヘッダー行がありません")

    headers = {_normalize_header(h) for h in reader.fieldnames if h}
    if not _REQUIRED_COLUMNS.issubset(headers):
        missing = ", ".join(sorted(_REQUIRED_COLUMNS - headers))
        raise HTTPException(
            status_code=400,
            detail=f"必須列が不足しています: {missing}",
        )

    rows: list[dict] = []
    for line_no, raw in enumerate(reader, start=2):
        row = {_normalize_header(k): (v or "").strip() for k, v in raw.items() if k}
        date = row.get("date", "")
        if not _DATE_PATTERN.match(date):
            raise HTTPException(
                status_code=400,
                detail=f"{line_no} 行目: date は YYYY-MM-DD 形式で指定してください",
            )
        try:
            student_id = int(row.get("student_id", ""))
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"{line_no} 行目: student_id は整数で指定してください",
            ) from exc
        if student_id < 1:
            raise HTTPException(status_code=400, detail=f"{line_no} 行目: student_id は 1 以上です")

        student_name = row.get("student_name", "")
        subject = row.get("subject", "")
        if not student_name or not subject:
            raise HTTPException(
                status_code=400,
                detail=f"{line_no} 行目: student_name と subject は必須です",
            )

        rows.append(
            {
                "date": date,
                "student_id": student_id,
                "student_name": student_name,
                "subject": subject,
            }
        )

    if not rows:
        raise HTTPException(status_code=400, detail="取り込めるデータ行がありません")

    return rows


def import_assignment_requests_from_csv(content: str) -> tuple[int, int, dict[str, int]]:
    rows = parse_assignment_requests_csv(content)
    by_date: dict[str, list[dict]] = {}
    for row in rows:
        by_date.setdefault(row["date"], []).append(
            {
                "student_id": row["student_id"],
                "student_name": row["student_name"],
                "subject": row["subject"],
            }
        )

    imported = 0
    skipped = 0
    summary: dict[str, int] = {}
    for date, requests in by_date.items():
        added, dup = append_assignment_requests(date, requests)
        imported += added
        skipped += dup
        summary[date] = added

    return imported, skipped, summary
