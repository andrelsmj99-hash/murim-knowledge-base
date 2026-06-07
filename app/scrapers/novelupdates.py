"""
NovelUpdates (novelupdates.com) metadata scraper.

NovelUpdates is the definitive directory for translated web-novels. It does NOT
host chapters — only metadata, reviews, and links to external translation sites.

This scraper extracts:
- Title (English + original)
- Author
- Genres / tags
- Description / synopsis
- Series status
- Associated translation links
"""
from __future__ import annotations

import logging
import re
from typing import Any

from bs4 import BeautifulSoup, FeatureNotFound

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

NOVELUPDATES_SELECTORS: dict[str, str] = {
    "title": ".seriestitlenu, .series-title h1, h1",
    "author": "#authtag a, a[href*='authtag']",
    "genres": "#seriesgenre a, .genre a, a[href*='genre']",
    "description": "#editdescription, .description, #synopsis",
    "status": "#showstatus, .status",
    "image": ".seriesimg img, .series-img img",
    "rank": ".rank, #rank",
    "rating": ".rating, #uvotes",
}


def _parse(html: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml")
    except FeatureNotFound:
        return BeautifulSoup(html, "html.parser")


class NovelUpdatesScraper(BaseScraper):
    """
    Scrapes novel metadata from NovelUpdates.

    Usage::

        scraper = NovelUpdatesScraper("my-novel-slug")
        meta = scraper.get_novel_metadata()
        # meta contains title, author, genres, description, etc.

    Does NOT support get_chapter_list or get_chapter_content since NU does not
    host chapters. Use this scraper for discovery/metadata, and pair it with a
    content scraper (e.g. NovelBinScraper) for chapter ingestion.
    """

    source_name: str = "novelupdates"

    def __init__(
        self,
        novel_slug: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(novel_slug, **kwargs)
        self.series_url = f"https://www.novelupdates.com/series/{novel_slug}/"

    def get_novel_metadata(self) -> dict[str, Any]:
        response = self._make_request(self.series_url)
        soup = _parse(response.text)

        title_el = soup.select_one(NOVELUPDATES_SELECTORS["title"])
        author_el = soup.select_one(NOVELUPDATES_SELECTORS["author"])
        desc_el = soup.select_one(NOVELUPDATES_SELECTORS["description"])
        status_el = soup.select_one(NOVELUPDATES_SELECTORS["status"])
        image_el = soup.select_one(NOVELUPDATES_SELECTORS["image"])
        rank_el = soup.select_one(NOVELUPDATES_SELECTORS["rank"])
        rating_el = soup.select_one(NOVELUPDATES_SELECTORS["rating"])

        genres: list[str] = []
        for tag in soup.select(NOVELUPDATES_SELECTORS["genres"]):
            genre = tag.get_text(strip=True)
            if genre:
                genres.append(genre)

        metadata: dict[str, Any] = {
            "title": title_el.get_text(strip=True) if title_el else self.novel_slug,
            "author": author_el.get_text(strip=True) if author_el else None,
            "genre": ", ".join(genres) if genres else None,
            "description": desc_el.get_text(" ", strip=True) if desc_el else None,
            "source_url": self.series_url,
            "language": "en",
        }

        if status_el:
            metadata["status"] = status_el.get_text(strip=True)
        if image_el and image_el.get("src"):
            metadata["cover_url"] = image_el.get("src")
        if rank_el:
            rank_text = rank_el.get_text(strip=True)
            match = re.search(r"(\d+)", rank_text)
            if match:
                metadata["rank"] = int(match.group(1))
        if rating_el:
            rating_text = rating_el.get_text(strip=True)
            match = re.search(r"(\d+\.?\d*)", rating_text)
            if match:
                metadata["rating"] = float(match.group(1))

        return metadata

    def get_chapter_list(self) -> list[dict[str, Any]]:
        logger.warning(
            "NovelUpdates does not host chapters. Use a content scraper (e.g. NovelBinScraper) "
            "for chapter content."
        )
        return []

    def get_chapter_content(self, chapter_info: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError(
            "NovelUpdates does not host chapter content. "
            "Use a content scraper (e.g. NovelBinScraper) for chapter content."
        )

