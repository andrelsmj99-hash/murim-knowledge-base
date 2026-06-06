from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.entities import Chapter, Novel
from app.core.use_cases import IngestChapterUseCase
from app.scrapers import get_scraper_class, list_sources
from app.scrapers.generic import GenericScraper


def test_repository_roundtrip(sqlite_uow):
    with sqlite_uow as uow:
        novel = uow.novels.upsert(
            Novel(
                title="Coiling Dragon",
                author="I Eat Tomatoes",
                source_url="https://example.com",
                language="en",
            )
        )
        assert novel.id is not None
        ch = uow.novels.add_chapter(
            Chapter(novel_id=novel.id, chapter_number=1, title="Chapter 1", content="word " * 100)
        )
        uow.commit()
        assert ch.word_count == 100
        chapters = uow.novels.get_chapters(novel.id)
        assert len(chapters) == 1


def test_use_case_ingest_idempotent(sqlite_session_factory):
    novel_meta = {"title": "Desolate Era", "author": "I Eat Tomatoes", "language": "en"}
    chapter_payload = {
        "chapter_number": 1,
        "title": "Chapter 1 — The Drop of Blood",
        "content": "It was a bright morning...",
    }
    from app.core.unit_of_work import UnitOfWork

    uow = UnitOfWork(session_factory=sqlite_session_factory)
    with uow:
        uc = IngestChapterUseCase(uow)
        r1 = uc.execute(novel_meta, chapter_payload)
        assert not r1.skipped
    uow2 = UnitOfWork(session_factory=sqlite_session_factory)
    with uow2:
        uc = IngestChapterUseCase(uow2)
        r2 = uc.execute(novel_meta, chapter_payload)
        assert r2.skipped
        assert r1.chapter_id == r2.chapter_id


def test_scraper_registry():
    assert "generic" in list_sources()
    cls = get_scraper_class("generic")
    assert cls.__name__ == "GenericScraper"


def test_generic_scraper_dry_run():
    progress_dir = Path(tempfile.mkdtemp(prefix="murim_test_"))
    scraper = GenericScraper(
        novel_slug="test",
        index_url="http://example.com/index",
        base_url="http://example.com",
        reverse_chapter_list=False,
        progress_dir=progress_dir,
    )
    index_html = """
    <html><body>
      <ul class="chapter-list">
        <li><a href="/ch/1">Chapter 1 — First</a></li>
        <li><a href="/ch/2">Chapter 2 — Second</a></li>
        <li><a href="/ch/3">Chapter 3 — Third</a></li>
      </ul>
    </body></html>
    """
    chapter_html = """
    <html><body>
      <h1>Chapter X</h1>
      <div id="chapter-content">Hello world.</div>
    </body></html>
    """
    responses = {
        "http://example.com/index": index_html,
        "http://example.com/ch/1": chapter_html,
        "http://example.com/ch/2": chapter_html,
        "http://example.com/ch/3": chapter_html,
    }

    def fake_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.text = responses[url]
        resp.status_code = 200
        return resp

    scraper.session.get = fake_get
    chapters = scraper.scrape_novel()
    assert len(chapters) == 3
    assert chapters[0]["chapter_number"] == 1
    assert "Hello world" in chapters[0]["content"]


def test_end_to_end_scrape_into_db(sqlite_session_factory):
    from app.core.unit_of_work import UnitOfWork

    progress_dir = Path(tempfile.mkdtemp(prefix="murim_e2e_"))
    index_html = """
    <html><body>
      <h1>Coiling Dragon</h1>
      <a class="author" href="#">I Eat Tomatoes</a>
      <div class="description">A modern-day story.</div>
      <ul class="chapter-list">
        <li><a href="/ch/1">Chapter 1 — Ring</a></li>
        <li><a href="/ch/2">Chapter 2 — Mountain</a></li>
      </ul>
    </body></html>
    """
    chapter_html = """
    <html><body>
      <h1>Chapter 1 — Ring</h1>
      <div id="chapter-content">It was a cold winter day. Lin Lei looked at the ring.</div>
    </body></html>
    """
    responses = {
        "http://example.com/index": index_html,
        "http://example.com/ch/1": chapter_html,
        "http://example.com/ch/2": chapter_html,
    }

    uow = UnitOfWork(session_factory=sqlite_session_factory)
    with uow:
        scraper = GenericScraper(
            novel_slug="coiling-dragon",
            index_url="http://example.com/index",
            base_url="http://example.com",
            reverse_chapter_list=False,
            progress_dir=progress_dir,
            ingest_use_case=IngestChapterUseCase(uow),
        )

        def fake_get(url, *args, **kwargs):
            resp = MagicMock()
            resp.text = responses[url]
            resp.status_code = 200
            return resp
        scraper.session.get = fake_get

        chapters = scraper.scrape_novel()
        assert len(chapters) == 2
        assert all(c["db_novel_id"] for c in chapters)

    uow2 = UnitOfWork(session_factory=sqlite_session_factory)
    with uow2:
        assert uow2.novels.count() == 1
        novel = uow2.novels.list(limit=1)[0]
        assert novel.title == "Coiling Dragon"
        assert novel.author == "I Eat Tomatoes"
        chapters_db = uow2.novels.get_chapters(novel.id)
        assert len(chapters_db) == 2
        assert [c.chapter_number for c in chapters_db] == [1, 2]
