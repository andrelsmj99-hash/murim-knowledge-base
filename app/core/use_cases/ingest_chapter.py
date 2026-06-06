"""
Use case: ingest a chapter payload coming from a scraper.

Responsibilities:
- upsert the parent novel (matched by title + author)
- skip the chapter if it has already been ingested (idempotency)
- persist the chapter and commit the transaction
- return a small :class:`IngestResult` summarizing what happened
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.core.entities import Chapter, Novel
from app.core.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    """Outcome of :class:`IngestChapterUseCase`."""

    novel_id: str
    chapter_id: str
    chapter_number: int
    skipped: bool  # True if the chapter was already in the DB
    word_count: int

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        state = "skipped" if self.skipped else "inserted"
        return f"IngestResult(novel={self.novel_id}, chapter={self.chapter_number}, {state})"


class IngestChapterUseCase:
    """
    Persist a single chapter to the database, creating the novel if necessary.

    The use case is intentionally tiny — it only handles persistence. NLP
    extraction, dedup, and graph construction are separate use cases.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def execute(
        self,
        novel_meta: dict,
        chapter_payload: dict,
    ) -> IngestResult:
        """
        :param novel_meta: ``{title, author, genre, description, source_url, language}``
        :param chapter_payload: ``{chapter_number, title, content, url}``
        """
        novel = Novel(
            title=(novel_meta.get("title") or "").strip(),
            author=(novel_meta.get("author") or None),
            genre=novel_meta.get("genre"),
            description=novel_meta.get("description"),
            source_url=novel_meta.get("source_url"),
            language=novel_meta.get("language") or "en",
        )
        if not novel.title:
            raise ValueError("novel_meta['title'] is required")

        novel = self.uow.novels.upsert(novel)

        chapter = Chapter(
            novel_id=novel.id,
            chapter_number=int(chapter_payload["chapter_number"]),
            title=chapter_payload.get("title"),
            content=chapter_payload.get("content", ""),
        )
        if not chapter.content:
            raise ValueError("chapter_payload['content'] is required")

        skipped = self.uow.novels.chapter_exists(novel.id, chapter.chapter_number)
        chapter = self.uow.novels.add_chapter(chapter)
        self.uow.commit()

        result = IngestResult(
            novel_id=novel.id,
            chapter_id=chapter.id,
            chapter_number=chapter.chapter_number,
            skipped=skipped,
            word_count=chapter.word_count,
        )
        logger.info("Ingested chapter %s (skipped=%s)", result.chapter_number, result.skipped)
        return result
