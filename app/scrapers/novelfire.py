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

# Default selectors — tuned for novelfire.net DOM as of 2026-06
NOVELFIRE_SELECTORS: dict[str, str] = {
    # Novel metadata (from /book/{slug} page)
    "novel_title": "h1.novel-title",
    "novel_author": "a[href*='/author/']",
    "novel_description": "div.description p",
    "novel_cover": ".book-cover img",
    "novel_genres": ".genres a",
    "novel_status": ".status",
    # Chapter list (from /book/{slug}/chapters page, paginated)
    "chapter_list_container": "ul.chapter-list",
    "chapter_list_item": "ul.chapter-list li a",
    "chapter_no": "span.chapter-no",
    "chapter_title_in_list": "strong.chapter-title",
    "chapter_update": "time.chapter-update",
    # Chapter content (from /book/{slug}/chapter-{N})
    "chapter_title": "h1.titles span.chapter-title",
    "chapter_content": "#content",
    "next_chapter": "a.btn-next-chapter",
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
        chapter_list_pages: int = 5,
        **kwargs: Any,
    ) -> None:
        super().__init__(novel_slug, **kwargs)
        self.domain = domain
        self.index_url = index_url or f"https://{domain}/book/{novel_slug}"
        self._base_url = f"https://{domain}"
        self.selectors = {**NOVELFIRE_SELECTORS, **(selectors or {})}
        self.chapter_list_pages = chapter_list_pages

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
        """Scrape all chapter list pages (paginated 100/chapter) and return full list."""
        chapters: list[dict[str, Any]] = []
        seen: set[int] = set()

        for page in range(1, self.chapter_list_pages + 1):
            list_url = f"{self.index_url}/chapters?page={page}"
            try:
                response = self._make_request(list_url)
            except Exception as exc:
                logger.warning("Failed to fetch chapter list page %d: %s", page, exc)
                break

            soup = _parse(response.text)
            container = soup.select_one(self.selectors["chapter_list_container"])
            if not container:
                logger.info("No more chapter list pages at page %d", page)
                break

            anchors = list(container.select(self.selectors["chapter_list_item"]))
            if not anchors:
                logger.info("No chapters found on page %d, stopping", page)
                break

            for anchor in anchors:
                href = anchor.get("href")
                if not href:
                    continue
                href_str = str(href)
                number = self._extract_number(href_str)
                if number is None or number in seen:
                    continue
                seen.add(number)

                # Extract title from <strong class="chapter-title"> inside the anchor
                title_el = anchor.select_one(self.selectors["chapter_title_in_list"])
                title = title_el.get_text(strip=True) if title_el else f"Chapter {number}"

                chapters.append(
                    {
                        "chapter_number": number,
                        "title": title,
                        "url": self._absolute(href_str),
                    }
                )

            logger.info(
                "Page %d: found %d chapters so far (total: %d)",
                page,
                len(anchors),
                len(chapters),
            )

        chapters.sort(key=lambda c: c["chapter_number"])
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

        # Join <p> tags with double newlines for paragraph separation
        paragraphs = content_el.find_all("p")
        if paragraphs:
            text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        else:
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
