from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("APP_DEBUG", "false")

from app.api.dependencies import get_uow  # noqa: E402
from app.core.unit_of_work import UnitOfWork  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base  # noqa: E402

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


# ---------------------------------------------------------------------------
# E2E: Streamlit server fixture
# ---------------------------------------------------------------------------


def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> None:
    """Block until *host:port* accepts TCP connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.5)
    raise TimeoutError(f"Streamlit did not start on {host}:{port} within {timeout}s")


@pytest.fixture(scope="session")
def dashboard_base_url() -> Iterator[str]:
    """Start a Streamlit server for E2E tests and tear it down afterwards.

    If ``DASHBOARD_E2E_URL`` is already set the server is NOT started —
    the caller is responsible for the running instance.
    """
    existing = os.environ.get("DASHBOARD_E2E_URL")
    if existing:
        yield existing
        return

    port = 8501
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        os.path.join(PROJECT_ROOT, "app", "dashboard", "main.py"),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--server.address",
        "127.0.0.1",
        "--browser.gatherUsageStats",
        "false",
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=PROJECT_ROOT,
        preexec_fn=os.setsid,
    )
    try:
        _wait_for_port("127.0.0.1", port, timeout=30)
        url = f"http://127.0.0.1:{port}"
        os.environ["DASHBOARD_E2E_URL"] = url
        yield url
    finally:
        os.environ.pop("DASHBOARD_E2E_URL", None)
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait()
