from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
DASHBOARDS_DIR = DATA_DIR / "shift-dashboards"
LOCATIONS_DIR = BACKEND_DIR / "locations"
OUTPUT_DIR = BACKEND_DIR / "output"
DEFAULT_SHIFT_DATE = "2026-06-10"
DEFAULT_LOCATION_SLUG = "hakutei"
DATABASE_URL = f"sqlite:///{BACKEND_DIR / 'juku_shift.db'}"
