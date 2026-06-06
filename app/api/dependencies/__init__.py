"""
FastAPI dependency providers.

Wraps the UnitOfWork in a request-scoped lifecycle and offers a lazy
sentence-transformers encoder so it is only loaded when /search is hit.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

from app.core.unit_of_work import UnitOfWork
from app.models.base import SessionLocal
from app.utils.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Unit of Work
# ---------------------------------------------------------------------------


# Resolve the session factory lazily so tests can monkey-patch it.
def _session_factory():
    return SessionLocal()


def get_uow() -> UnitOfWork:
    """Yield an already-entered :class:`UnitOfWork` for the duration of a request."""
    uow = UnitOfWork(session_factory=_session_factory)
    uow.__enter__()
    try:
        yield uow
    finally:
        # UoW.__exit__ closes the session; use cases are expected to commit
        # explicitly, but if an exception escapes we still want a clean close.
        uow.__exit__(None, None, None)


# ---------------------------------------------------------------------------
# Embedding encoder (lazy singleton)
# ---------------------------------------------------------------------------


class _Encoder:
    """Lazy holder for the sentence-transformers model."""

    def __init__(self) -> None:
        self._model = None
        self._lock = threading.Lock()
        self._failed = False

    def get(self):
        if self._model is not None or self._failed:
            return self._model
        with self._lock:
            if self._model is not None or self._failed:
                return self._model
            try:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading sentence-transformers model %s", settings.transformers_model)
                self._model = SentenceTransformer(settings.transformers_model)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "sentence-transformers unavailable, /search will degrade gracefully: %s", exc
                )
                self._failed = True
                self._model = None
        return self._model

    def encode(self, text: str) -> Optional[list[float]]:
        model = self.get()
        if model is None:
            return None
        try:
            vec = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
            return [float(x) for x in vec.tolist()]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Embedding failed for %r: %s", text[:50], exc)
            return None


_encoder = _Encoder()


def get_encoder() -> _Encoder:
    """FastAPI dependency returning the shared encoder."""
    return _encoder
