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
    # period_base は class_schedules.is_fixed に統合。空 JSON のみ互換 seed。
    seed_period_bases_if_empty()
    seed_shift_submissions_if_empty()
    seed_admin_overrides_if_empty()
    seed_assignments_if_empty()
    seed_assignment_requests_if_empty()
    seed_shift_dashboards_if_empty()
    from services.entity_store import seed_entities_if_empty

    seed_entities_if_empty()
    from services.fiscal_year_store import ensure_current_fiscal_year

    ensure_current_fiscal_year()


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
        if "is_deleted" not in col_names:
            conn.execute(text("ALTER TABLE periods ADD COLUMN is_deleted INTEGER DEFAULT 0"))
            conn.commit()
        if "location_slug" not in col_names:
            conn.execute(
                text("ALTER TABLE periods ADD COLUMN location_slug VARCHAR(64) DEFAULT 'hakutei'")
            )
            conn.commit()
        if "period_kind" not in col_names:
            conn.execute(
                text("ALTER TABLE periods ADD COLUMN period_kind VARCHAR(10) DEFAULT 'CRAM'")
            )
            conn.commit()
        if "submission_deadline" not in col_names:
            conn.execute(text("ALTER TABLE periods ADD COLUMN submission_deadline DATE"))
            conn.commit()
        assign_cols = {
            row[1] for row in conn.execute(text("PRAGMA table_info(assignments)")).fetchall()
        }
        if "lesson_kind" not in assign_cols:
            conn.execute(
                text("ALTER TABLE assignments ADD COLUMN lesson_kind VARCHAR(10) DEFAULT '講習'")
            )
            conn.commit()
        teacher_cols = {
            row[1] for row in conn.execute(text("PRAGMA table_info(teacher_profiles)")).fetchall()
        }
        if "max_lanes" not in teacher_cols:
            conn.execute(
                text("ALTER TABLE teacher_profiles ADD COLUMN max_lanes INTEGER DEFAULT 2")
            )
            conn.commit()
        plan_cols = {
            row[1] for row in conn.execute(text("PRAGMA table_info(student_subject_plans)")).fetchall()
        }
        if "teacher_id" not in plan_cols:
            conn.execute(text("ALTER TABLE student_subject_plans ADD COLUMN teacher_id INTEGER"))
            conn.commit()
        change_cols = {
            row[1] for row in conn.execute(text("PRAGMA table_info(shift_change_requests)")).fetchall()
        }
        if "request_type" not in change_cols:
            conn.execute(
                text(
                    "ALTER TABLE shift_change_requests ADD COLUMN request_type VARCHAR(20) DEFAULT 'SLOT'"
                )
            )
            conn.commit()
        from services.class_schedule_store import migrate_from_assignments_table

        migrate_from_assignments_table()
