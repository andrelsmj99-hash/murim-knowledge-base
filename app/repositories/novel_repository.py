"""
SQLAlchemy implementation of :class:`INovelRepository`.
"""
from __future__ import annotations

import builtins
import uuid as uuid_module

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.entities import Chapter, Novel
from app.core.interfaces import INovelRepository
from app.models.novel import Chapter as ChapterORM
from app.models.novel import Novel as NovelORM


def _to_uuid(value: str) -> uuid_module.UUID:
    return uuid_module.UUID(str(value))


def _novel_to_entity(orm: NovelORM) -> Novel:
    chapters = [_chapter_to_entity(c) for c in orm.chapters]
    return Novel(
        id=str(orm.id),
        title=orm.title,
        author=orm.author,
        genre=orm.genre,
        description=orm.description,
        source_url=orm.source_url,
        language=orm.language or "en",
        total_chapters=orm.total_chapters or 0,
        chapters=chapters,
    )


def _novel_to_orm(entity: Novel) -> NovelORM:
    return NovelORM(
        id=_to_uuid(entity.id),
        title=entity.title,
        author=entity.author,
        genre=entity.genre,
        description=entity.description,
        source_url=entity.source_url,
        language=entity.language,
        total_chapters=entity.total_chapters,
    )


def _chapter_to_entity(orm: ChapterORM) -> Chapter:
    return Chapter(
        id=str(orm.id),
        novel_id=str(orm.novel_id),
        chapter_number=orm.chapter_number,
        title=orm.title,
        content=orm.content,
        word_count=orm.word_count or 0,
    )


def _chapter_to_orm(entity: Chapter) -> ChapterORM:
    return ChapterORM(
        id=_to_uuid(entity.id),
        novel_id=_to_uuid(entity.novel_id),
        chapter_number=entity.chapter_number,
        title=entity.title,
        content=entity.content,
        word_count=entity.word_count or len(entity.content.split()),
    )


class NovelRepository(INovelRepository):
    entity_cls = Novel

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    # --- read -----------------------------------------------------------

    def get(self, entity_id: str) -> Novel | None:
        orm = self.session.get(NovelORM, _to_uuid(entity_id))
        return _novel_to_entity(orm) if orm else None

    def list(self, *, limit: int = 100, offset: int = 0) -> builtins.list[Novel]:
        stmt = select(NovelORM).order_by(NovelORM.title).limit(limit).offset(offset)
        return [_novel_to_entity(n) for n in self.session.execute(stmt).scalars().all()]

    def count(self) -> int:
        return int(self.session.scalar(select(func.count(NovelORM.id))) or 0)

    def get_by_title_author(self, title: str, author: str | None) -> Novel | None:
        stmt = select(NovelORM).where(NovelORM.title == title)
        if author:
            stmt = stmt.where(NovelORM.author == author)
        else:
            stmt = stmt.where(NovelORM.author.is_(None))
        orm = self.session.execute(stmt).scalar_one_or_none()
        return _novel_to_entity(orm) if orm else None

    def get_chapters(self, novel_id: str, *, limit: int = 1000, offset: int = 0) -> builtins.list[Chapter]:
        stmt = (
            select(ChapterORM)
            .where(ChapterORM.novel_id == _to_uuid(novel_id))
            .order_by(ChapterORM.chapter_number)
            .limit(limit)
            .offset(offset)
        )
        return [_chapter_to_entity(c) for c in self.session.execute(stmt).scalars().all()]

    def chapter_exists(self, novel_id: str, chapter_number: int) -> bool:
        stmt = (
            select(ChapterORM.id)
            .where(ChapterORM.novel_id == _to_uuid(novel_id), ChapterORM.chapter_number == chapter_number)
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def chapters_count(self, novel_id: str) -> int:
        stmt = select(func.count(ChapterORM.id)).where(ChapterORM.novel_id == _to_uuid(novel_id))
        return int(self.session.scalar(stmt) or 0)

    # --- write ----------------------------------------------------------

    def add(self, entity: Novel) -> Novel:
        orm = _novel_to_orm(entity)
        self.session.add(orm)
        self.session.flush()
        return _novel_to_entity(orm)

    def delete(self, entity_id: str) -> bool:
        orm = self.session.get(NovelORM, _to_uuid(entity_id))
        if orm is None:
            return False
        self.session.delete(orm)
        self.session.flush()
        return True

    def upsert(self, novel: Novel) -> Novel:
        existing = self.get_by_title_author(novel.title, novel.author)
        if existing:
            orm = self.session.get(NovelORM, _to_uuid(existing.id))
            orm.genre = novel.genre or orm.genre
            orm.description = novel.description or orm.description
            orm.source_url = novel.source_url or orm.source_url
            orm.language = novel.language or orm.language
            self.session.flush()
            return _novel_to_entity(orm)
        return self.add(novel)

    def add_chapter(self, chapter: Chapter) -> Chapter:
        if self.chapter_exists(chapter.novel_id, chapter.chapter_number):
            existing = self.session.execute(
                select(ChapterORM).where(
                    ChapterORM.novel_id == _to_uuid(chapter.novel_id),
                    ChapterORM.chapter_number == chapter.chapter_number,
                )
            ).scalar_one()
            return _chapter_to_entity(existing)
        orm = _chapter_to_orm(chapter)
        self.session.add(orm)
        novel_orm = self.session.get(NovelORM, _to_uuid(chapter.novel_id))
        if novel_orm is not None:
            novel_orm.total_chapters = (
                int(self.session.scalar(
                    select(func.count(ChapterORM.id)).where(ChapterORM.novel_id == _to_uuid(chapter.novel_id))
                ) or 0)
            )
        self.session.flush()
        return _chapter_to_entity(orm)
