"""
Novel and Chapter repository contract.
"""

from __future__ import annotations

import abc

from app.core.entities import Chapter, Novel
from app.core.interfaces.repository import IRepository


class INovelRepository(IRepository[Novel], abc.ABC):
    """Persistence operations for :class:`Novel` and its chapters."""

    @abc.abstractmethod
    def get_by_title_author(self, title: str, author: str | None) -> Novel | None:
        """Find a novel by its unique (title, author) key."""

    @abc.abstractmethod
    def upsert(self, novel: Novel) -> Novel:
        """Insert a novel or return the existing one matching the canonical key."""

    @abc.abstractmethod
    def add_chapter(self, chapter: Chapter) -> Chapter:
        """Insert a chapter for an existing novel (or no-op if duplicate)."""

    @abc.abstractmethod
    def get_chapters(self, novel_id: str, *, limit: int = 1000, offset: int = 0) -> list[Chapter]:
        """Return chapters for a novel, ordered by chapter number."""

    @abc.abstractmethod
    def chapter_exists(self, novel_id: str, chapter_number: int) -> bool:
        """Return ``True`` if a chapter with that number has already been ingested."""

    @abc.abstractmethod
    def chapters_count(self, novel_id: str) -> int:
        """Return the total number of chapters for a novel."""

    @abc.abstractmethod
    def get_novel_stats(self, novel_id: str) -> dict[str, int]:
        """Return aggregated stats for a novel: characters, orgs, locations, relationships, embeddings, archetypes."""
