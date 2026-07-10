import os
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

_DEV_JWT_SECRET = "dev-insecure-secret-change-me-before-deploying-to-prod"
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", _DEV_JWT_SECRET)
if JWT_SECRET_KEY == _DEV_JWT_SECRET:
    print(
        "[config] WARNING: JWT_SECRET_KEY is not set; using an insecure development "
        "default. Set the JWT_SECRET_KEY environment variable before deploying."
    )
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 12

_DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]
