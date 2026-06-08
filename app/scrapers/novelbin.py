"""
NovelBin (novelbin.com / novelbin.me) dedicated scraper.

NovelBin is one of the most popular aggregators for Murim / Wuxia / Xianxia
web-novels. It hosts complete translated novels with a consistent HTML structure.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, FeatureNotFound

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

NOVELBIN_SELECTORS: dict[str, str] = {
    "novel_title": "h3.title, h1.title, .novel-title, h2",
    "novel_author": ".author a, a[href*='author-'], .info-meta span:contains('Author')",
    "novel_description": ".desc-text, .description, .summary, .short-description",
    "chapter_list_container": "#list-chapter, ul.list-chapter, .chapter-list, .list-chapter",
    "chapter_list_item": "li a, a.chapter, .chr-item a",
    "chapter_title": "h2.chapter-title, h1, a.chr-title, span.chr-text",
    "chapter_content": "#chr-content, .chr-c, #chapter-content, .chapter-content, .reading-content",
}


def _parse(html: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml")
    except FeatureNotFound:
        return BeautifulSoup(html, "html.parser")


class NovelBinScraper(BaseScraper):
    source_name: str = "novelbin"

    def __init__(
        self,
        novel_slug: str,
        index_url: str | None = None,
        domain: str = "novelbin.com",
        **kwargs: Any,
    ) -> None:
        super().__init__(novel_slug, **kwargs)
        self.domain = domain
        self.index_url = index_url or f"https://{domain}/novel-book/{novel_slug}"
        self._base_url = f"https://{domain}"

    def _absolute(self, href: str) -> str:
        if href.startswith(("http://", "https://")):
            return href
        return urljoin(self._base_url + "/", href.lstrip("/"))

    @staticmethod
    def _extract_number(text: str) -> int | None:
        import re

        match = re.search(r"(\d+)", text or "")
        return int(match.group(1)) if match else None

    def get_novel_metadata(self) -> dict[str, Any]:
        response = self._make_request(self.index_url)
        soup = _parse(response.text)

        title_el = soup.select_one(NOVELBIN_SELECTORS["novel_title"])
        author_el = soup.select_one(NOVELBIN_SELECTORS["novel_author"])
        desc_el = soup.select_one(NOVELBIN_SELECTORS["novel_description"])

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

        container = soup.select_one(NOVELBIN_SELECTORS["chapter_list_container"])
        if not container:
            logger.warning("No chapter list container found for %s", self.novel_slug)
            return []

        anchors = list(container.select(NOVELBIN_SELECTORS["chapter_list_item"]))
        anchors = list(reversed(anchors))

        chapters: list[dict[str, Any]] = []
        seen: set[int] = set()

        for anchor in anchors:
            href = anchor.get("href")
            text = anchor.get_text(" ", strip=True)
            if not href or not isinstance(href, str):
                continue
            number = self._extract_number(text)
            if number is None or number in seen:
                continue
            seen.add(number)
            chapters.append(
                {
                    "chapter_number": number,
                    "title": text,
                    "url": self._absolute(href),
                }
            )
        return chapters

    def get_chapter_content(self, chapter_info: dict[str, Any]) -> dict[str, Any] | None:
        import re

        url = chapter_info["url"]
        response = self._make_request(url)
        soup = _parse(response.text)

        for tag in soup.select("script, style, ins, iframe, .ads, .advertisement, .ad-block"):
            tag.decompose()

        content_el = soup.select_one(NOVELBIN_SELECTORS["chapter_content"])
        if content_el is None:
            logger.warning("No content found at %s", url)
            return None

        text = content_el.get_text("\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not text:
            return None

        title_el = soup.select_one(NOVELBIN_SELECTORS["chapter_title"])
        title = title_el.get_text(strip=True) if title_el else chapter_info.get("title")

        return {
            "chapter_number": chapter_info["chapter_number"],
            "title": title,
            "content": text,
            "word_count": len(text.split()),
            "url": url,
        }
