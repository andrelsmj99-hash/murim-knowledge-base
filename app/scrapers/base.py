"""
Base scraper class with retry, rate limiting, and progress persistence.

Design:
- Scraping (network IO) is decoupled from persistence (DB).
- Subclasses only implement `get_chapter_list` and `get_chapter_content`.
- Progress is persisted as JSON so a scrape can be safely resumed.
"""

from __future__ import annotations

import abc
import json
import logging
import random
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.utils.config import settings

logger = logging.getLogger(__name__)


# Exceptions worth retrying on (network/transient HTTP errors)
_RETRYABLE = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.HTTPError,
    requests.exceptions.ChunkedEncodingError,
)


class BaseScraper(abc.ABC):
    """Abstract base class for all novel scrapers."""

    #: Human-readable label of the source (e.g. "novelbin", "wuxiaworld").
    source_name: str = "generic"

    def __init__(
        self,
        novel_slug: str,
        session: requests.Session | None = None,
        progress_dir: Path | None = None,
        ingest_use_case: Any | None = None,
    ) -> None:
        self.novel_slug = novel_slug
        self.session = session or self._build_session()
        self.ingest_use_case = ingest_use_case

        self.progress_dir = progress_dir or settings.progress_dir
        self.progress_dir.mkdir(parents=True, exist_ok=True)
        self.progress_file = self.progress_dir / f"progress_{self.source_name}_{novel_slug}.json"

        self.chapters: list[dict[str, Any]] = []

    # ------------------------------------------------------------------ session

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        return session

    # ------------------------------------------------------------------ network

    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE),
        reraise=True,
    )
    def _make_request(self, url: str, **kwargs: Any) -> requests.Response:
        """HTTP GET with exponential back-off retry and randomized rate limiting."""
        delay = random.uniform(settings.scraper_delay_min, settings.scraper_delay_max)
        logger.debug("Sleeping %.2fs before request to %s", delay, url)
        time.sleep(delay)

        logger.info("GET %s", url)
        response = self.session.get(url, timeout=30, **kwargs)

        # Treat 429 as retryable
        if response.status_code == 429:
            logger.warning("429 Too Many Requests for %s", url)
            raise requests.exceptions.HTTPError("429 Too Many Requests", response=response)

        response.raise_for_status()
        return response

    # --------------------------------------------------------- abstract methods

    @abc.abstractmethod
    def get_chapter_list(self) -> list[dict[str, Any]]:
        """Return a list of chapter descriptors: ``[{chapter_number, title, url}, ...]``."""

    @abc.abstractmethod
    def get_chapter_content(self, chapter_info: dict[str, Any]) -> dict[str, Any] | None:
        """Return a full chapter payload or ``None`` if it cannot be scraped.

        Expected keys: ``chapter_number, title, content, word_count, url``.
        """

    @abc.abstractmethod
    def get_novel_metadata(self) -> dict[str, Any]:
        """Return novel-level metadata: ``{title, author, genre, description, source_url}``."""

    # ---------------------------------------------------------------- iteration

    def iter_chapters(self, resume: bool = True) -> Iterator[dict[str, Any]]:
        """Yield chapter payloads one by one, persisting progress after each."""
        logger.info("Starting scrape of '%s' from %s", self.novel_slug, self.source_name)

        processed = set(self._load_progress().get("processed_chapters", []))
        if resume and processed:
            logger.info("Resuming — %d chapter(s) already processed.", len(processed))

        chapter_list = self.get_chapter_list()
        logger.info("Found %d chapter(s) in index.", len(chapter_list))

        for info in chapter_list:
            number = info.get("chapter_number")
            if resume and number in processed:
                logger.debug("Skipping chapter %s (already processed).", number)
                continue

            try:
                data = self.get_chapter_content(info)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to scrape chapter %s: %s", number, exc)
                continue

            if not data:
                logger.warning("Empty payload for chapter %s, skipping.", number)
                continue

            self._save_progress(data)
            yield data

    def scrape_novel(self, resume: bool = True) -> list[dict[str, Any]]:
        """Materialize all chapters and persist to DB if ``ingest_use_case`` is set.

        Subclasses may override this method for custom persistence logic.
        """
        self.chapters = []
        if self.ingest_use_case is None:
            logger.info(
                "Scrape complete — %d chapter(s) collected (no DB persistence).", len(self.chapters)
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

    # ------------------------------------------------------------ progress I/O

    def _load_progress(self) -> dict[str, Any]:
        if not self.progress_file.exists():
            return {"processed_chapters": [], "last_chapter": None}
        try:
            with self.progress_file.open("r", encoding="utf-8") as fh:
                data: dict[str, Any] = json.load(fh)
            data.setdefault("processed_chapters", [])
            return data
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Could not load progress file %s: %s", self.progress_file, exc)
            return {"processed_chapters": [], "last_chapter": None}

    def _save_progress(self, chapter_data: dict[str, Any]) -> None:
        try:
            progress = self._load_progress()
            number = chapter_data.get("chapter_number")
            if number is not None and number not in progress["processed_chapters"]:
                progress["processed_chapters"].append(number)
            # Store last chapter without the (potentially huge) content
            progress["last_chapter"] = {k: v for k, v in chapter_data.items() if k != "content"}
            with self.progress_file.open("w", encoding="utf-8") as fh:
                json.dump(progress, fh, indent=2, ensure_ascii=False)
        except OSError as exc:
            logger.error("Could not write progress file %s: %s", self.progress_file, exc)

    def is_chapter_processed(self, chapter_number: int) -> bool:
        return chapter_number in set(self._load_progress().get("processed_chapters", []))
