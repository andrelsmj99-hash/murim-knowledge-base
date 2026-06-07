"""
A configurable concrete scraper that works with most Murim/Wuxia sites that
expose a simple "list of chapters" + "single chapter" pattern.

Subclasses (or configurations) just need to provide the two URL templates and
CSS selectors — everything else (retry, rate-limit, progress, DB persistence)
is handled by the base class and the injected use case.
"""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, FeatureNotFound

from app.core.use_cases import IngestChapterUseCase
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


def _parse(html: str) -> BeautifulSoup:
    """Parse with lxml if available, else fall back to the stdlib parser."""
    try:
        return BeautifulSoup(html, "lxml")
    except FeatureNotFound:
        return BeautifulSoup(html, "html.parser")


# ---------------------------------------------------------------------------
# Default selectors — overridable per source
# ---------------------------------------------------------------------------

DEFAULT_SELECTORS = {
    "chapter_list_container": "ul.chapter-list, .chapter-list, #chapter-list, #list",
    "chapter_list_item": "li a, a.chapter, .ch-item a",
    "chapter_title_fallback": "h1, .chapter-title, .title",
    "chapter_content": "#chapter-content, .chapter-content, .chapter-inner, .text-content, #content",
    "next_chapter": "a.next, .nav-next a, #next",
}


class GenericScraper(BaseScraper):
    """
    Configurable HTML scraper.

    Required parameters at construction time:

    - ``index_url``: page that lists all chapters
    - ``base_url``:  base URL used to resolve relative chapter links

    The two ``sel_*`` parameters let callers override the default CSS
    selectors without subclassing.
    """

    source_name: str = "generic"

    def __init__(
        self,
        novel_slug: str,
        index_url: str,
        base_url: str,
        ingest_use_case: IngestChapterUseCase | None = None,
        selectors: dict[str, str] | None = None,
        reverse_chapter_list: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(novel_slug, **kwargs)
        if not index_url:
            raise ValueError("index_url is required for GenericScraper")
        self.index_url = index_url
        self.base_url = base_url.rstrip("/")
        self.ingest_use_case = ingest_use_case
        self.selectors = {**DEFAULT_SELECTORS, **(selectors or {})}
        self.reverse_chapter_list = reverse_chapter_list

    # ------------------------------------------------------------------ helpers

    def _absolute(self, href: str) -> str:
        return urljoin(self.base_url + "/", href.lstrip("/"))

    @staticmethod
    def _parse_chapter_number(text: str) -> int | None:
        """Extract the first integer from a string like 'Chapter 12' or 'Ch. 12 - …'."""
        match = re.search(r"\d+", text or "")
        return int(match.group()) if match else None

    # ----------------------------------------------------------- abstract impl

    def get_novel_metadata(self) -> dict[str, Any]:
        """Best-effort novel metadata extraction; callers can override it."""
        response = self._make_request(self.index_url)
        soup = _parse(response.text)

        title_el = soup.select_one("h1, .novel-title, .book-title, .post-title")
        author_el = soup.select_one(".author a, .author, a[href*='author']")
        desc_el = soup.select_one("#description, .description, .summary")

        return {
            "title": title_el.get_text(strip=True) if title_el else self.novel_slug,
            "author": author_el.get_text(strip=True) if author_el else None,
            "genre": None,
            "description": desc_el.get_text(" ", strip=True) if desc_el else None,
            "source_url": self.index_url,
            "language": "en",
        }

    def get_chapter_list(self) -> list[dict[str, Any]]:
        response = self._make_request(self.index_url)
        soup = _parse(response.text)

        container = soup.select_one(self.selectors["chapter_list_container"]) or soup
        chapters: list[dict[str, Any]] = []
        seen_numbers: set[int] = set()

        # Many novel sites list chapters newest-first; reverse so we ingest
        # in canonical reading order.
        anchors = list(container.select(self.selectors["chapter_list_item"]))
        if self.reverse_chapter_list:
            anchors = list(reversed(anchors))

        for anchor in anchors:
            href = anchor.get("href")
            text = anchor.get_text(" ", strip=True)
            if not href:
                continue
            number = self._parse_chapter_number(text)
            if number is None or number in seen_numbers:
                continue
            seen_numbers.add(number)
            chapters.append(
                {
                    "chapter_number": number,
                    "title": text,
                    "url": self._absolute(href),
                }
            )
        return chapters

    def get_chapter_content(self, chapter_info: dict[str, Any]) -> dict[str, Any] | None:
        url = chapter_info["url"]
        response = self._make_request(url)
        soup = _parse(response.text)

        # Remove noise
        for tag in soup.select("script, style, ins, iframe, .ads, .ad"):
            tag.decompose()

        content_el = soup.select_one(self.selectors["chapter_content"])
        if content_el is None:
            logger.warning("No content found at %s using %s", url, self.selectors["chapter_content"])
            return None

        text = content_el.get_text("\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not text:
            return None

        title_el = soup.select_one(self.selectors["chapter_title_fallback"])
        title = title_el.get_text(strip=True) if title_el else chapter_info.get("title")

        return {
            "chapter_number": chapter_info["chapter_number"],
            "title": title,
            "content": text,
            "word_count": len(text.split()),
            "url": url,
        }

    # ----------------------------------------------------------- persistence

    def scrape_novel(self, resume: bool = True) -> list[dict[str, Any]]:
        """
        Materialize all chapters and persist them to the DB if a use case was
        injected. Falls back to plain iteration when ``ingest_use_case`` is
        ``None`` (useful for dry-runs or local JSON dumps).
        """
        self.chapters = []
        if self.ingest_use_case is None:
            logger.warning(
                "GenericScraper running without an IngestChapterUseCase — chapters "
                "will only be kept in memory and progress JSON."
            )
            self.chapters = list(self.iter_chapters(resume=resume))
            return self.chapters

        meta = self.get_novel_metadata()
        logger.info("Novel metadata resolved: %s", meta.get("title"))
        for chapter_payload in self.iter_chapters(resume=resume):
            result = self.ingest_use_case.execute(meta, chapter_payload)
            self.chapters.append(
                {
                    **chapter_payload,
                    "db_novel_id": result.novel_id,
                    "db_chapter_id": result.chapter_id,
                    "skipped": result.skipped,
                }
            )
        logger.info("Scrape + ingest complete — %d chapter(s).", len(self.chapters))
        return self.chapters
