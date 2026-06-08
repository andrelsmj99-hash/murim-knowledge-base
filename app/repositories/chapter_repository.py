"""
SQLAlchemy implementation of :class:`IChapterRepository`.
"""

from __future__ import annotations

import builtins
import uuid as uuid_module

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.entities import Chapter
from app.core.interfaces import IChapterRepository
from app.models.character import Character as CharacterORM
from app.models.novel import Chapter as ChapterORM


def _to_uuid(value: str) -> uuid_module.UUID:
    return uuid_module.UUID(str(value))


def _chapter_to_entity(orm: ChapterORM) -> Chapter:
    return Chapter(
        id=str(orm.id),
        novel_id=str(orm.novel_id),
        chapter_number=orm.chapter_number,
        title=orm.title,
        content=orm.content,
        word_count=orm.word_count or 0,
    )


class ChapterRepository(IChapterRepository):
    entity_cls = Chapter

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    # --- read -----------------------------------------------------------

    def get(self, entity_id: str) -> Chapter | None:
        orm = self.session.get(ChapterORM, _to_uuid(entity_id))
        return _chapter_to_entity(orm) if orm else None

    def list(self, *, limit: int = 100, offset: int = 0) -> builtins.list[Chapter]:
        stmt = (
            select(ChapterORM)
            .order_by(ChapterORM.novel_id, ChapterORM.chapter_number)
            .limit(limit)
            .offset(offset)
        )
        return [_chapter_to_entity(c) for c in self.session.execute(stmt).scalars().all()]

    def count(self) -> int:
        return int(self.session.scalar(select(func.count(ChapterORM.id))) or 0)

    def get_by_novel(
        self, novel_id: str, *, limit: int = 1000, offset: int = 0
    ) -> builtins.list[Chapter]:
        stmt = (
            select(ChapterORM)
            .where(ChapterORM.novel_id == _to_uuid(novel_id))
            .order_by(ChapterORM.chapter_number)
            .limit(limit)
            .offset(offset)
        )
        return [_chapter_to_entity(c) for c in self.session.execute(stmt).scalars().all()]

    def get_chapters_by_character(self, character_id: str) -> builtins.list[Chapter]:
        """Return all chapters where a character appears by name or aliases in title/content."""
        # Get the character to find name and aliases
        char_orm = self.session.get(CharacterORM, _to_uuid(character_id))
        if char_orm is None:
            return []

        # Build search terms: character name + all alias values
        search_terms = [char_orm.name]
        for alias in char_orm.aliases:
            search_terms.append(alias.alias_value)

        # Search chapters where title or content contains any of the search terms
        conditions = []
        for term in search_terms:
            if term:
                pattern = f"%{term}%"
                conditions.append(ChapterORM.title.ilike(pattern))
                conditions.append(ChapterORM.content.ilike(pattern))

        if not conditions:
            return []

        stmt = (
            select(ChapterORM)
            .where(or_(*conditions))
            .order_by(ChapterORM.novel_id, ChapterORM.chapter_number)
            .distinct()
        )
        return [_chapter_to_entity(c) for c in self.session.execute(stmt).scalars().all()]

    def search_by_content(self, query: str, *, limit: int = 100) -> builtins.list[Chapter]:
        if not query:
            return []
        pattern = f"%{query}%"
        stmt = (
            select(ChapterORM)
            .where(ChapterORM.content.ilike(pattern))
            .order_by(ChapterORM.novel_id, ChapterORM.chapter_number)
            .limit(limit)
        )
        return [_chapter_to_entity(c) for c in self.session.execute(stmt).scalars().all()]

    # --- write ----------------------------------------------------------

    def add(self, entity: Chapter) -> Chapter:
        orm = ChapterORM(
            id=_to_uuid(entity.id),
            novel_id=_to_uuid(entity.novel_id),
            chapter_number=entity.chapter_number,
            title=entity.title,
            content=entity.content,
            word_count=entity.word_count or len(entity.content.split()),
        )
        self.session.add(orm)
        self.session.flush()
        return _chapter_to_entity(orm)

    def delete(self, entity_id: str) -> bool:
        orm = self.session.get(ChapterORM, _to_uuid(entity_id))
        if orm is None:
            return False
        self.session.delete(orm)
        self.session.flush()
        return True
