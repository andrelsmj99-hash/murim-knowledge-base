"""
Domain entity for the Novel aggregate (independent of ORM).
"""
from __future__ import annotations

import uuid as uuid_module
from dataclasses import dataclass, field


@dataclass
class Chapter:
    """A single chapter of a novel."""

    id: str = field(default_factory=lambda: str(uuid_module.uuid4()))
    novel_id: str = ""
    chapter_number: int = 0
    title: str | None = None
    content: str = ""
    word_count: int = 0
    url: str | None = None  # not persisted, useful for the scraper layer

    def __post_init__(self) -> None:
        if self.word_count == 0 and self.content:
            self.word_count = len(self.content.split())

    def snippet(self, max_chars: int = 280) -> str:
        """Return a short, single-line preview of the content."""
        cleaned = " ".join(self.content.split())
        if len(cleaned) <= max_chars:
            return cleaned
        return cleaned[: max_chars - 1].rstrip() + "…"


@dataclass
class Novel:
    """Top-level novel metadata and chapter list."""

    id: str = field(default_factory=lambda: str(uuid_module.uuid4()))
    title: str = ""
    author: str | None = None
    genre: str | None = None
    description: str | None = None
    source_url: str | None = None
    language: str = "en"
    total_chapters: int = 0
    chapters: list[Chapter] = field(default_factory=list)

    def add_chapter(self, chapter: Chapter) -> None:
        """Append a chapter, keeping the chapter count consistent."""
        chapter.novel_id = self.id
        self.chapters.append(chapter)
        self.total_chapters = len(self.chapters)

    @property
    def canonical_key(self) -> tuple[str, str | None]:
        """Stable key used for deduplication (matches the DB unique constraint)."""
        return (self.title.strip().lower(), (self.author or "").strip().lower() or None)
