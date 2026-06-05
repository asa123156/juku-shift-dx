from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
DASHBOARDS_DIR = DATA_DIR / "shift-dashboards"
DEFAULT_SHIFT_DATE = "2026-06-10"
