"""
/novels and /novels/{id}/chapters routes.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.schemas import (
    ChapterCreate,
    ChapterDetail,
    ChapterRead,
    NovelCreate,
    NovelRead,
    Page,
    PageMeta,
)
from app.core.entities import Chapter, Novel
from app.core.interfaces import INovelRepository
from app.core.unit_of_work import UnitOfWork
from app.api.dependencies import get_uow

router = APIRouter()


def _uow_novels(uow: UnitOfWork) -> INovelRepository:
    return uow.novels


@router.get("", response_model=Page)
def list_novels(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    uow: UnitOfWork = Depends(get_uow),
) -> Page:
    repo = _uow_novels(uow)
    items: List[NovelRead] = [NovelRead.model_validate(n) for n in repo.list(limit=limit, offset=offset)]
    return Page(items=items, meta=PageMeta(total=repo.count(), limit=limit, offset=offset))


@router.get("/{novel_id}", response_model=NovelRead)
def get_novel(novel_id: str, uow: UnitOfWork = Depends(get_uow)) -> NovelRead:
    novel = _uow_novels(uow).get(novel_id)
    if novel is None:
        raise HTTPException(status_code=404, detail="Novel not found")
    return NovelRead.model_validate(novel)


@router.post("", response_model=NovelRead, status_code=status.HTTP_201_CREATED)
def create_novel(payload: NovelCreate, uow: UnitOfWork = Depends(get_uow)) -> NovelRead:
    repo = _uow_novels(uow)
    existing = repo.get_by_title_author(payload.title, payload.author)
    if existing is not None:
        return NovelRead.model_validate(existing)
    novel = Novel(
        title=payload.title,
        author=payload.author,
        genre=payload.genre,
        description=payload.description,
        source_url=payload.source_url,
        language=payload.language or "en",
    )
    created = repo.add(novel)
    uow.commit()
    return NovelRead.model_validate(created)


@router.get("/{novel_id}/chapters", response_model=Page)
def list_chapters(
    novel_id: str,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    uow: UnitOfWork = Depends(get_uow),
) -> Page:
    repo = _uow_novels(uow)
    if repo.get(novel_id) is None:
        raise HTTPException(status_code=404, detail="Novel not found")
    chapters = repo.get_chapters(novel_id, limit=limit, offset=offset)
    items = [
        ChapterRead(
            id=c.id,
            novel_id=c.novel_id,
            chapter_number=c.chapter_number,
            title=c.title,
            word_count=c.word_count,
            snippet=c.snippet(280),
        )
        for c in chapters
    ]
    total = repo.chapters_count(novel_id)
    return Page(
        items=items,
        meta=PageMeta(total=total, limit=limit, offset=offset),
    )


@router.get(
    "/{novel_id}/chapters/{chapter_number}",
    response_model=ChapterDetail,
)
def get_chapter(
    novel_id: str,
    chapter_number: int,
    uow: UnitOfWork = Depends(get_uow),
) -> ChapterDetail:
    repo = _uow_novels(uow)
    if repo.get(novel_id) is None:
        raise HTTPException(status_code=404, detail="Novel not found")
    for ch in repo.get_chapters(novel_id, limit=10_000):
        if ch.chapter_number == chapter_number:
            return ChapterDetail(
                id=ch.id,
                novel_id=ch.novel_id,
                chapter_number=ch.chapter_number,
                title=ch.title,
                word_count=ch.word_count,
                snippet=ch.snippet(280),
                content=ch.content,
            )
    raise HTTPException(status_code=404, detail="Chapter not found")


@router.post(
    "/{novel_id}/chapters",
    response_model=ChapterRead,
    status_code=status.HTTP_201_CREATED,
)
def add_chapter(
    novel_id: str,
    payload: ChapterCreate,
    uow: UnitOfWork = Depends(get_uow),
) -> ChapterRead:
    repo = _uow_novels(uow)
    if repo.get(novel_id) is None:
        raise HTTPException(status_code=404, detail="Novel not found")
    chapter = Chapter(
        novel_id=novel_id,
        chapter_number=payload.chapter_number,
        title=payload.title,
        content=payload.content,
    )
    stored = repo.add_chapter(chapter)
    uow.commit()
    return ChapterRead(
        id=stored.id,
        novel_id=stored.novel_id,
        chapter_number=stored.chapter_number,
        title=stored.title,
        word_count=stored.word_count,
        snippet=stored.snippet(280),
    )
