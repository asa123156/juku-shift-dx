from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import admin, auth, lessons, shifts

app = FastAPI(
    title="JUKU-SHIFT DX API",
    description="個別指導塾シフト管理 API",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(shifts.router)
app.include_router(admin.router)
app.include_router(lessons.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.2.0"}
