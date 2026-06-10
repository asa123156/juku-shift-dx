import csv
import io

from fastapi import HTTPException

from services.period_store import get_period, iter_dates, set_period_base_slot
from services.schedule_service import build_my_schedule
from services.shift_store import get_teacher_submission
from services.student_store import get_student_submission

_REQUIRED = {"role", "entity_id", "date", "slot", "symbol"}


def _normalize_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def import_shift_excel_csv(period_id: int, content: str) -> int:
    period = get_period(period_id)
    if period.status not in ("DRAFT", "COLLECTING"):
        raise HTTPException(status_code=409, detail="Import only allowed in DRAFT or COLLECTING")

    allowed_dates = set(iter_dates(period.start_date, period.end_date))
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="CSV header missing")

    headers = {_normalize_header(h) for h in reader.fieldnames if h}
    if not _REQUIRED.issubset(headers):
        missing = ", ".join(sorted(_REQUIRED - headers))
        raise HTTPException(status_code=400, detail=f"Missing columns: {missing}")

    count = 0
    for line_no, raw in enumerate(reader, start=2):
        row = {_normalize_header(k): (v or "").strip() for k, v in raw.items() if k}
        role = row.get("role", "").lower()
        if role not in ("teacher", "student"):
            raise HTTPException(status_code=400, detail=f"Line {line_no}: role must be teacher or student")

        iso_date = row.get("date", "")
        if iso_date not in allowed_dates:
            raise HTTPException(status_code=400, detail=f"Line {line_no}: date outside period")

        try:
            entity_id = int(row.get("entity_id", ""))
            slot = str(int(row.get("slot", "")))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Line {line_no}: invalid entity_id or slot") from exc

        if slot not in ("1", "2", "3", "4"):
            raise HTTPException(status_code=400, detail=f"Line {line_no}: slot must be 1-4")

        symbol = row.get("symbol", "")
        if symbol != "◎":
            raise HTTPException(status_code=400, detail=f"Line {line_no}: import symbol must be ◎")

        set_period_base_slot(period_id, role, entity_id, iso_date, slot, symbol)
        count += 1
    return count


def export_shift_excel_csv(period_id: int) -> str:
    period = get_period(period_id)
    dates = iter_dates(period.start_date, period.end_date)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["role", "entity_id", "date", "slot", "symbol"])

    for iso_date in dates:
        for teacher_id in (1, 2, 3):
            slots = get_teacher_submission(teacher_id, iso_date) or {"1": "", "2": "", "3": "", "4": ""}
            for slot in ("1", "2", "3", "4"):
                writer.writerow(["teacher", teacher_id, iso_date, slot, slots.get(slot, "")])

        for student_id in (1, 2, 3):
            slots = get_student_submission(student_id, iso_date) or {"1": "", "2": "", "3": "", "4": ""}
            for slot in ("1", "2", "3", "4"):
                writer.writerow(["student", student_id, iso_date, slot, slots.get(slot, "")])

    return output.getvalue()
