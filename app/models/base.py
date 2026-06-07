"""
SQLAlchemy Base and Database Configuration.

Uses :class:`app.utils.config.settings` as the single source of truth for the
database URL, removing duplication with ``os.getenv`` and ensuring consistency
across the application (including Alembic).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.utils.config import settings


def _build_engine_kwargs(url: str) -> dict:
    """Engine kwargs that adapt to the underlying dialect.

    SQLite uses a :class:`SingletonThreadPool` which forbids ``max_overflow``;
    the production PostgreSQL engine wants pool sizing + pre-ping.
    """
    if url.startswith("sqlite"):
        return {"echo": settings.app_debug, "connect_args": {"check_same_thread": False}}
    return {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "echo": settings.app_debug,
    }


engine = create_engine(settings.database_url, **_build_engine_kwargs(settings.database_url))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Session:
    """FastAPI dependency that yields a database session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
