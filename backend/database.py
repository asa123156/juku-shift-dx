from collections.abc import Generator

from sqlalchemy import create_engine
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
    from services.admin_store import seed_admin_overrides_if_empty
    from services.period_store import seed_period_bases_if_empty, seed_periods_if_empty
    from services.submission_store import seed_shift_submissions_if_empty

    seed_periods_if_empty()
    seed_period_bases_if_empty()
    seed_shift_submissions_if_empty()
    seed_admin_overrides_if_empty()
