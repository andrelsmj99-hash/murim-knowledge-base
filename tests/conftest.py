from __future__ import annotations

import os
import sys
from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("APP_DEBUG", "false")

from app.core.unit_of_work import UnitOfWork
from app.models import Base

SAMPLE_CHAPTER = """
Chapter 12 — The Baruch Estate

The morning sun rose over Jianghu as Elder Lin Lei of the Baruch family
strode across the courtyard. He was the master of the Mount Hua Sect, and
his disciple, Lei Hu, followed respectfully behind.

"Lin Lei is the senior brother of Yi Yun," the old servant whispered.
"Lin Lei is the rival of Di Shi. Di Shi's master is Qing Yan."

Far to the north, in the Heavenly Demon Cult, the Demon King brooded.
The Righteous Alliance and the Unholy Union had been at war for centuries.

The journey led them across the Central Plains and through the Jianghu
to the Imperial City. They passed Mount Hua, then Wudang Mountain, before
finally reaching the Hidden Dragon Hall in the capital.
""".strip()


@pytest.fixture
def sqlite_session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture
def sqlite_uow(sqlite_session_factory) -> Iterator[UnitOfWork]:
    uow = UnitOfWork(session_factory=sqlite_session_factory)
    uow.__enter__()
    try:
        yield uow
    finally:
        uow.__exit__(None, None, None)


@pytest.fixture
def sample_chapter() -> str:
    return SAMPLE_CHAPTER


@pytest.fixture
def api_client():
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.api.dependencies import get_uow

    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    test_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def _override_get_uow() -> Iterator[UnitOfWork]:
        uow = UnitOfWork(session_factory=test_session_factory)
        uow.__enter__()
        try:
            yield uow
        finally:
            uow.__exit__(None, None, None)

    app = create_app()
    app.dependency_overrides[get_uow] = _override_get_uow

    with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())

    return TestClient(app), test_session_factory
