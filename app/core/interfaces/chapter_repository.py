"""
Chapter repository contract.
"""

from __future__ import annotations

import abc

from app.core.entities import Chapter
from app.core.interfaces.repository import IRepository


class IChapterRepository(IRepository[Chapter], abc.ABC):
    """Persistence operations for :class:`Chapter` aggregates."""

    @abc.abstractmethod
    def get_by_novel(self, novel_id: str, *, limit: int = 1000, offset: int = 0) -> list[Chapter]:
        """Return chapters for a novel, ordered by chapter number."""

    @abc.abstractmethod
    def get_chapters_by_character(self, character_id: str) -> list[Chapter]:
        """Return all chapters where a character appears by name or aliases."""

    @abc.abstractmethod
    def search_by_content(self, query: str, *, limit: int = 100) -> list[Chapter]:
        """Search chapters by content substring."""
