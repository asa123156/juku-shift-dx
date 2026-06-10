import json
from pathlib import Path

from fastapi import HTTPException

from config import DATA_DIR, REPO_ROOT
from services.dashboard_store import list_shift_dates


def _read_json(path: Path) -> object:
    if not path.is_file():
        raise HTTPException(
            status_code=500,
            detail=f"Data file not found: {path.relative_to(REPO_ROOT)}",
        )
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def resolve_shift_date(date: str | None) -> str:
    from config import DEFAULT_SHIFT_DATE

    dates = list_shift_dates()
    if not dates:
        raise HTTPException(status_code=500, detail="No shift dashboard data configured")
    if date is None:
        return DEFAULT_SHIFT_DATE if DEFAULT_SHIFT_DATE in dates else dates[0]
    if date not in dates:
        raise HTTPException(
            status_code=404,
            detail=f"No shift dashboard for date={date}. Available: {', '.join(dates)}",
        )
    return date


def load_users() -> list[dict]:
    path = DATA_DIR / "users.json"
    data = _read_json(path)
    if not isinstance(data, list):
        raise HTTPException(status_code=500, detail="users.json must be a JSON array")
    return data


def load_lessons(date: str | None = None) -> list[dict]:
    path = REPO_ROOT / "docs" / "lesson_mock.json"
    data = _read_json(path)
    if not isinstance(data, list):
        raise HTTPException(status_code=500, detail="lesson_mock.json must be a JSON array")
    if date is None:
        return data
    return [row for row in data if row.get("date") == date]
