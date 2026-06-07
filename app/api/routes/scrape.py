from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_uow
from app.api.schemas import ScrapeChapterItem, ScrapeRequest, ScrapeResponse
from app.core.unit_of_work import UnitOfWork
from app.scrapers import make_scraper

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ScrapeResponse)
def trigger_scrape(
    payload: ScrapeRequest,
    uow: UnitOfWork = Depends(get_uow),
) -> ScrapeResponse:
    kwargs: dict[str, Any] = {}
    if payload.index_url:
        kwargs["index_url"] = payload.index_url
    if payload.base_url:
        kwargs["base_url"] = payload.base_url
    if payload.domain:
        kwargs["domain"] = payload.domain
    kwargs.setdefault("reverse_chapter_list", payload.reverse_chapter_list)

    try:
        scraper = make_scraper(
            source=payload.source,
            novel_slug=payload.novel_slug,
            uow=uow,
            **kwargs,
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    chapters: list[dict[str, Any]] = scraper.scrape_novel(resume=payload.resume)
    items: list[ScrapeChapterItem] = []
    errors: list[str] = []
    novel_id: str | None = None
    novel_title: str | None = None

    for ch in chapters:
        item = ScrapeChapterItem(
            chapter_number=ch.get("chapter_number", 0),
            title=ch.get("title"),
            db_chapter_id=ch.get("db_chapter_id"),
            skipped=ch.get("skipped", False),
        )
        items.append(item)
        novel_id = ch.get("db_novel_id", novel_id)

    try:
        novel_title = scraper.get_novel_metadata().get("title")
    except Exception:
        novel_title = None

    return ScrapeResponse(
        novel_slug=payload.novel_slug,
        novel_title=novel_title,
        novel_id=novel_id,
        total=len(items),
        chapters=items,
        errors=errors,
    )
