"""
Scraper registry / factory — lets callers resolve a scraper by source name
and run a one-line ingestion.

Example::

    from app.scrapers import run_scrape
    from app.core.unit_of_work import UnitOfWork

    with UnitOfWork() as uow:
        run_scrape("generic", "coiling-dragon", index_url=..., base_url=..., uow=uow)
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.unit_of_work import UnitOfWork
from app.core.use_cases import IngestChapterUseCase
from app.scrapers.base import BaseScraper
from app.scrapers.generic import GenericScraper
from app.scrapers.novelbin import NovelBinScraper
from app.scrapers.novelfire import NovelFireScraper
from app.scrapers.novelupdates import NovelUpdatesScraper
from app.scrapers.wuxiaworld import WuxiaWorldScraper

logger = logging.getLogger(__name__)


_REGISTRY: dict[str, type[BaseScraper]] = {
    "generic": GenericScraper,
    "novelbin": NovelBinScraper,
    "novelupdates": NovelUpdatesScraper,
    "novelfire": NovelFireScraper,
    "wuxiaworld": WuxiaWorldScraper,
}


def register_scraper(source_name: str, scraper_cls: type[BaseScraper]) -> None:
    """Register a new scraper class under a lowercase source name."""
    if not issubclass(scraper_cls, BaseScraper):
        raise TypeError(f"{scraper_cls!r} must subclass BaseScraper")
    _REGISTRY[source_name.lower()] = scraper_cls
    logger.info("Registered scraper %s -> %s", source_name, scraper_cls.__name__)


def get_scraper_class(source_name: str) -> type[BaseScraper]:
    key = source_name.lower()
    if key not in _REGISTRY:
        raise KeyError(f"Unknown source '{source_name}'. Available: {sorted(_REGISTRY)}")
    return _REGISTRY[key]


def list_sources() -> list[str]:
    """Return the registered source names."""
    return sorted(_REGISTRY)


def make_scraper(
    source: str,
    novel_slug: str,
    uow: UnitOfWork | None = None,
    **kwargs: Any,
) -> BaseScraper:
    """Instantiate a scraper, optionally wiring it to a DB-bound use case."""
    cls = get_scraper_class(source)
    if uow is not None:
        kwargs.setdefault("ingest_use_case", IngestChapterUseCase(uow))
    return cls(novel_slug=novel_slug, **kwargs)


def run_scrape(
    source: str,
    novel_slug: str,
    *,
    uow: UnitOfWork,
    **kwargs: Any,
) -> list[dict]:
    """Convenience helper: build a scraper, run it, return the chapter list."""
    scraper = make_scraper(source, novel_slug, uow=uow, **kwargs)
    return scraper.scrape_novel()
