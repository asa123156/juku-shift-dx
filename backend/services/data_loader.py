import json
from pathlib import Path

from fastapi import HTTPException

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


def _read_json(path: Path) -> object:
    if not path.is_file():
        raise HTTPException(
            status_code=500,
            detail=f"Data file not found: {path.relative_to(REPO_ROOT)}",
        )
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_shift_dashboard(date: str | None = None, *, apply_submissions: bool = True) -> dict:
    from services.shift_store import apply_submissions_to_dashboard

    path = BACKEND_DIR / "data" / "shift-dashboard.json"
    data = _read_json(path)
    if date is not None and data.get("date") != date:
        raise HTTPException(
            status_code=404,
            detail=f"No shift dashboard for date={date}",
        )
    if apply_submissions:
        data = apply_submissions_to_dashboard(data)
    return data


def load_lessons() -> list[dict]:
    path = REPO_ROOT / "docs" / "lesson_mock.json"
    data = _read_json(path)
    if not isinstance(data, list):
        raise HTTPException(status_code=500, detail="lesson_mock.json must be a JSON array")
    return data
