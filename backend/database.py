from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    import models  # noqa: F401 — register ORM models with Base.metadata

    Base.metadata.create_all(bind=engine)
    migrate_sqlite_schema()
    from services.admin_store import seed_admin_overrides_if_empty
    from services.assignment_store import seed_assignment_requests_if_empty, seed_assignments_if_empty
    from services.dashboard_store import seed_shift_dashboards_if_empty
    from services.period_store import seed_period_bases_if_empty, seed_periods_if_empty
    from services.submission_store import seed_shift_submissions_if_empty

    seed_periods_if_empty()
    seed_period_bases_if_empty()
    seed_shift_submissions_if_empty()
    seed_admin_overrides_if_empty()
    seed_assignments_if_empty()
    seed_assignment_requests_if_empty()
    seed_shift_dashboards_if_empty()
    from services.entity_store import seed_entities_if_empty

    seed_entities_if_empty()


def migrate_sqlite_schema() -> None:
    """既存 DB に不足列があれば追加する（SQLite）。"""
    if not DATABASE_URL.startswith("sqlite"):
        return
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(periods)")).fetchall()
        col_names = {row[1] for row in rows}
        if "closed_dates" not in col_names:
            conn.execute(text("ALTER TABLE periods ADD COLUMN closed_dates JSON DEFAULT '[]'"))
            conn.commit()
        assign_cols = {
            row[1] for row in conn.execute(text("PRAGMA table_info(assignments)")).fetchall()
        }
        if "lesson_kind" not in assign_cols:
            conn.execute(
                text("ALTER TABLE assignments ADD COLUMN lesson_kind VARCHAR(10) DEFAULT '講習'")
            )
            conn.commit()
