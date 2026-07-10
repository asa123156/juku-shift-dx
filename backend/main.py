import importlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import CORS_ALLOWED_ORIGINS, REPO_ROOT
from database import init_db
from routers import admin, auth, calendar, export, google, lessons, shifts

import_router = importlib.import_module("routers.import")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="JUKU-SHIFT DX API",
    description="個別指導塾シフト管理 API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(shifts.router)
app.include_router(calendar.router)
app.include_router(admin.router)
app.include_router(admin.shared_router)
app.include_router(lessons.router)
app.include_router(import_router.router)
app.include_router(export.router)
app.include_router(google.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.2.0"}


# frontend/dist があれば同一オリジンで SPA を配信する（Vite dev サーバー利用時は不要）。
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        candidate = FRONTEND_DIST / full_path
        if full_path and ".." not in full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
