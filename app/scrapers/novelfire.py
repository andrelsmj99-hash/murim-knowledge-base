"""
NovelFire (novelfire.net) dedicated scraper.

NovelFire is a popular aggregator for translated web-novels including Murim/Wuxia/Xianxia.
This scraper uses configurable CSS selectors with sensible defaults for the site's structure.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, FeatureNotFound

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Default selectors — may need adjustment based on actual site structure
NOVELFIRE_SELECTORS: dict[str, str] = {
    "novel_title": "h1.novel-title, h1.book-title, .novel-info h1, .book-info h1, h1",
    "novel_author": ".author a, .author-info a, a[href*='/author/'], .info-author a",
    "novel_description": ".description, .novel-desc, .book-desc, .summary, #description",
    "novel_cover": ".novel-cover img, .book-cover img, .cover img",
    "novel_genres": ".genres a, .tags a, .categories a, .genre a",
    "novel_status": ".status, .novel-status, .book-status",
    "chapter_list_container": "#chapter-list, .chapter-list, .list-chapter, ul.chapters, .chapter-items",
    "chapter_list_item": "li a, .chapter-item a, .ch-item a, a.chapter-link",
    "chapter_title": "h1.chapter-title, h1.entry-title, .chapter-title, h1",
    "chapter_content": "#chapter-content, .chapter-content, .reading-content, .text-content, .entry-content",
    "next_chapter": "a.next, .nav-next a, a[rel='next']",
}


def _parse(html: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml")
    except FeatureNotFound:
        return BeautifulSoup(html, "html.parser")


class NovelFireScraper(BaseScraper):
    """
    Scrapes novels from novelfire.net.

    Usage::

        scraper = NovelFireScraper("novel-slug")
        meta = scraper.get_novel_metadata()
        chapters = scraper.get_chapter_list()
        for ch in chapters:
            content = scraper.get_chapter_content(ch)
            # process content...

    Supports optional custom selectors via kwargs for sites with different structures.
    """

    source_name: str = "novelfire"

    def __init__(
        self,
        novel_slug: str,
        index_url: str | None = None,
        domain: str = "novelfire.net",
        selectors: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(novel_slug, **kwargs)
        self.domain = domain
        self.index_url = index_url or f"https://{domain}/novel/{novel_slug}"
        self._base_url = f"https://{domain}"
        self.selectors = {**NOVELFIRE_SELECTORS, **(selectors or {})}

    def _absolute(self, href: str) -> str:
        if href.startswith(("http://", "https://")):
            return href
        return urljoin(self._base_url + "/", href.lstrip("/"))

    @staticmethod
    def _extract_number(text: str) -> int | None:
        match = re.search(r"(\d+)", text or "")
        return int(match.group(1)) if match else None

    def get_novel_metadata(self) -> dict[str, Any]:
        response = self._make_request(self.index_url)
        soup = _parse(response.text)

        title_el = soup.select_one(self.selectors["novel_title"])
        author_el = soup.select_one(self.selectors["novel_author"])
        desc_el = soup.select_one(self.selectors["novel_description"])
        cover_el = soup.select_one(self.selectors["novel_cover"])
        status_el = soup.select_one(self.selectors["novel_status"])
        genre_els = soup.select(self.selectors["novel_genres"])

        genres = [g.get_text(strip=True) for g in genre_els if g.get_text(strip=True)]

        return {
            "title": title_el.get_text(strip=True) if title_el else self.novel_slug,
            "author": author_el.get_text(strip=True) if author_el else None,
            "genre": ", ".join(genres) if genres else None,
            "description": desc_el.get_text(" ", strip=True) if desc_el else None,
            "cover_url": cover_el.get("src") if cover_el else None,
            "status": status_el.get_text(strip=True) if status_el else None,
            "source_url": self.index_url,
            "language": "en",
        }

    def get_chapter_list(self) -> list[dict[str, Any]]:
        response = self._make_request(self.index_url)
        soup = _parse(response.text)

        container = soup.select_one(self.selectors["chapter_list_container"])
        if not container:
            logger.warning(
                "No chapter list container found for %s at %s", self.novel_slug, self.index_url
            )
            # Fallback: try finding any links that look like chapters
            container = soup

        anchors = list(container.select(self.selectors["chapter_list_item"]))

        # Many sites list chapters newest-first; reverse to get reading order
        anchors = list(reversed(anchors))

        chapters: list[dict[str, Any]] = []
        seen: set[int] = set()

        for anchor in anchors:
            href = anchor.get("href")
            text = anchor.get_text(" ", strip=True)
            if not href:
                continue
            href_str = str(href) if href else ""
            number = self._extract_number(text)
            if number is None or number in seen:
                continue
            seen.add(number)
            chapters.append(
                {
                    "chapter_number": number,
                    "title": text,
                    "url": self._absolute(href_str),
                }
            )

        logger.info("Found %d chapter(s) for %s", len(chapters), self.novel_slug)
        return chapters

    def get_chapter_content(self, chapter_info: dict[str, Any]) -> dict[str, Any] | None:
        url = chapter_info["url"]
        response = self._make_request(url)
        soup = _parse(response.text)

        # Remove noise elements
        for tag in soup.select(
            "script, style, ins, iframe, .ads, .advertisement, .ad-block, .adsbygoogle"
        ):
            tag.decompose()

        content_el = soup.select_one(self.selectors["chapter_content"])
        if content_el is None:
            logger.warning(
                "No content found at %s using selector %s", url, self.selectors["chapter_content"]
            )
            return None

        text = content_el.get_text("\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not text:
            return None

        title_el = soup.select_one(self.selectors["chapter_title"])
        title = title_el.get_text(strip=True) if title_el else chapter_info.get("title")

        return {
            "chapter_number": chapter_info["chapter_number"],
            "title": title,
            "content": text,
            "word_count": len(text.split()),
            "url": url,
        }
