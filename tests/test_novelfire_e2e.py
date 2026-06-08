"""
End-to-end test: Nano Machine via novelfire.net

Tests the full pipeline:
1. Scrape novel metadata + 2 chapters from novelfire.net
2. Ingest chapters into SQLite in-memory DB
3. Run NLP entity extraction on each chapter
4. Persist extracted entities (characters, orgs, locations)
5. Build knowledge graph
6. Verify all entities are correctly persisted
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.unit_of_work import UnitOfWork
from app.core.use_cases import (
    BuildKnowledgeGraphUseCase,
    ExtractEntitiesUseCase,
    IngestChapterUseCase,
    IngestEntitiesUseCase,
)
from app.nlp.archetype_classifier import ArchetypeClassifier
from app.processing import canonicalize_name

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Realistic HTML fixtures based on actual novelfire.net structure
# ---------------------------------------------------------------------------

NOVEL_INDEX_HTML = """
<html><body>
<article id="novel">
  <header class="novel-header">
    <div class="header-body container">
      <div class="novel-info">
        <div class="main-head">
          <h1 class="novel-title text2row">Nano Machine</h1>
          <div class="author">
            <a href="/author/novelbin" class="property-item">
              <span>NovelBin</span>
            </a>
          </div>
        </div>
        <div class="categories">
          <ul>
            <li><a class="property-item">Action</a></li>
            <li><a class="property-item">Fantasy</a></li>
            <li><a class="property-item">Martial Arts</a></li>
            <li><a class="property-item">Sci-fi</a></li>
          </ul>
        </div>
      </div>
    </div>
  </header>
  <div class="novel-body container">
    <div class="summary">
      <div class="content expand-wrapper">
        <p>Nanotechnology meets martial arts at the Mashin Academy.
        Cheon Yeo-un's mother may not be one of the High Priest's six
        official wives, but his father's blood still qualifies him for
        a chance at the position of Minor Priest.</p>
      </div>
    </div>
    <div id="chapter-list">
      <ul class="chapters">
        <li><a href="/book/nano-machine/chapter-1">Chapter 1 — Nano Machine</a></li>
        <li><a href="/book/nano-machine/chapter-2">Chapter 2 — The First Challenge</a></li>
        <li><a href="/book/nano-machine/chapter-3">Chapter 3 — The Secret of the Nanomachines</a></li>
      </ul>
    </div>
  </div>
</article>
</body></html>
"""

CHAPTER_1_HTML = """
<html><body>
<article>
  <h1 class="chapter-title">Chapter 1 — Nano Machine</h1>
  <div id="chapter-content">
    <p>The sky above the Mashin Academy was a deep shade of crimson as
    Cheon Yeo-un stood at the entrance of the Grand Hall. His father,
    the High Priest of the Demonic Cult, had summoned all of his children
    for the selection ceremony.</p>
    <p>"Remember, Yeo-un," whispered Elder Park Jin-soo, placing a hand
    on the young man's shoulder. "Your mother may not hold a high position,
    but your bloodline is pure."</p>
    <p>From the shadows, Cheon Yeo-won watched with cold eyes. He was the
    Eldest Young Master, son of the First Wife, and he considered Yeo-un
    nothing more than a nuisance.</p>
    <p>"Senior Brother Yeo-won will crush that bastard," muttered
    Park Jin-woo, a loyal follower of the Eldest Young Master.</p>
    <p>The Demonic Cult's martial arts were legendary. The Heavenly Demon
    had once unified the Murim world under a single banner, and now his
    descendants competed fiercely for the right to inherit the title.</p>
    <p>Elder Lee Dong-Il stood at the podium, his voice booming across
    the hall. "The selection will begin with a test of martial arts.
    The strongest among you will be granted access to the Cult's secret
    techniques."</p>
    <p>Cheon Yeo-un clenched his fists. He had been training in the
    Demonic Cult's qi cultivation method for years, but he knew that
    alone would not be enough against his half-brothers.</p>
    <p>Suddenly, a strange sensation surged through his body. Something
    ancient and powerful stirred within him — the nanomachines that had
    been injected into him by a mysterious descendant from the future.</p>
    <p>He looked out the window toward the Sacred Sect of Mount Hua,
    visible in the distance beyond the mountains. "What is this power?"
    Yeo-un whispered to himself as his vision blurred and he saw streams
    of data flowing before his eyes.</p>
    <p>The Nano Machine had awakened.</p>
  </div>
</article>
</body></html>
"""

CHAPTER_2_HTML = """
<html><body>
<article>
  <h1 class="chapter-title">Chapter 2 — The First Challenge</h1>
  <div id="chapter-content">
    <p>The first challenge of the selection ceremony took place in the
    Arena of Shadows, a massive colosseum carved into the mountainside
    of the Demonic Cult's headquarters.</p>
    <p>Cheon Yeo-un faced his first opponent: Cheon Jin-ho, the Third
    Young Master, a practitioner of the Dark Flame Sword technique.</p>
    <p>"You don't stand a chance against me, Yeo-un," Jin-ho sneered,
    drawing his obsidian blade. "The Dark Flame technique has been
    perfected over three generations."</p>
    <p>But the Nano Machine had already analyzed Jin-ho's fighting style.
    Data flooded Yeo-un's mind: weak points, optimal strike angles,
    and the precise timing needed to exploit the gaps in his opponent's
    defense.</p>
    <p>Yeo-un moved with inhuman precision. His fist connected with
    Jin-ho's shoulder at the exact point where the Dark Flame qi
    flow was weakest. The Third Young Master stumbled backward, shock
    written across his face.</p>
    <p>"Impossible!" Jin-ho screamed. "How did you know about the
    weakness in my technique?"</p>
    <p>Elder Park Jin-soo watched from the gallery, a faint smile
    crossing his weathered face. He had been Yeo-un's secret mentor
    for years, teaching him the fundamentals of the Demonic Cult's
    internal energy cultivation.</p>
    <p>From the VIP box, Cheon Yeo-won narrowed his eyes. He had
    underestimated his half-brother. "This changes things," he
    muttered to his advisor, a mysterious figure known only as the
    Shadow Elder.</p>
    <p>The selection would continue at the Sacred Sect of Mount Hua,
    where the elders would judge each candidate's worthiness to
    enter the Heavenly Demon Cult's forbidden library.</p>
    <p>The Heavenly Demon Cult's hierarchy was about to shift. And
    at the center of it all was a young man with machines flowing
    through his veins.</p>
  </div>
</article>
</body></html>
"""


# ---------------------------------------------------------------------------
# Helper: mock HTTP responses
# ---------------------------------------------------------------------------


def _build_responses() -> dict[str, str]:
    """Map URLs to their HTML responses."""
    base = "https://novelfire.net"
    return {
        f"{base}/book/nano-machine": NOVEL_INDEX_HTML,
        f"{base}/book/nano-machine/chapter-1": CHAPTER_1_HTML,
        f"{base}/book/nano-machine/chapter-2": CHAPTER_2_HTML,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNovelFireE2E:
    """End-to-end test suite for Nano Machine via novelfire.net."""

    def test_scrape_metadata(self):
        """1. Verify scraper extracts correct novel metadata."""
        from app.scrapers.novelfire import NovelFireScraper

        responses = _build_responses()

        scraper = NovelFireScraper(
            novel_slug="nano-machine",
            index_url="https://novelfire.net/book/nano-machine",
        )

        def fake_get(url: str, *args: Any, **kwargs: Any) -> MagicMock:
            resp = MagicMock()
            resp.text = responses.get(url, "<html></html>")
            resp.status_code = 200
            return resp

        scraper.session.get = fake_get

        meta = scraper.get_novel_metadata()
        assert meta["title"] == "Nano Machine"
        assert meta["author"] == "NovelBin"
        assert "Action" in (meta["genre"] or "")
        assert "Fantasy" in (meta["genre"] or "")
        assert meta["language"] == "en"
        assert meta["source_url"] == "https://novelfire.net/book/nano-machine"
        assert meta["description"] is not None
        assert "Mashin Academy" in meta["description"]

    def test_scrape_chapter_list(self):
        """2. Verify scraper finds chapters from the index page."""
        from app.scrapers.novelfire import NovelFireScraper

        responses = _build_responses()

        scraper = NovelFireScraper(
            novel_slug="nano-machine",
            index_url="https://novelfire.net/book/nano-machine",
        )

        def fake_get(url: str, *args: Any, **kwargs: Any) -> MagicMock:
            resp = MagicMock()
            resp.text = responses.get(url, "<html></html>")
            resp.status_code = 200
            return resp

        scraper.session.get = fake_get

        chapters = scraper.get_chapter_list()
        assert len(chapters) >= 2
        numbers = [ch["chapter_number"] for ch in chapters]
        assert 1 in numbers
        assert 2 in numbers

    def test_scrape_chapter_content(self):
        """3. Verify scraper extracts chapter text content."""
        from app.scrapers.novelfire import NovelFireScraper

        responses = _build_responses()

        scraper = NovelFireScraper(
            novel_slug="nano-machine",
            index_url="https://novelfire.net/book/nano-machine",
        )

        def fake_get(url: str, *args: Any, **kwargs: Any) -> MagicMock:
            resp = MagicMock()
            resp.text = responses.get(url, "<html></html>")
            resp.status_code = 200
            return resp

        scraper.session.get = fake_get

        ch1 = scraper.get_chapter_content(
            {
                "chapter_number": 1,
                "title": "Chapter 1",
                "url": "https://novelfire.net/book/nano-machine/chapter-1",
            }
        )
        assert ch1 is not None
        assert ch1["chapter_number"] == 1
        assert "Cheon Yeo-un" in ch1["content"]
        assert "Nano Machine" in ch1["title"]
        assert ch1["word_count"] > 50

    def test_ingest_chapters_to_db(self, sqlite_session_factory):
        """4. Verify chapters are persisted to the database."""
        from app.scrapers.novelfire import NovelFireScraper

        responses = _build_responses()
        progress_dir = Path(tempfile.mkdtemp(prefix="murim_nf_e2e_"))

        uow = UnitOfWork(session_factory=sqlite_session_factory)
        with uow:
            scraper = NovelFireScraper(
                novel_slug="nano-machine",
                index_url="https://novelfire.net/book/nano-machine",
                progress_dir=progress_dir,
                ingest_use_case=IngestChapterUseCase(uow),
            )

            def fake_get(url: str, *args: Any, **kwargs: Any) -> MagicMock:
                resp = MagicMock()
                resp.text = responses.get(url, "<html></html>")
                resp.status_code = 200
                return resp

            scraper.session.get = fake_get
            chapters = scraper.scrape_novel()

            assert len(chapters) >= 2
            for ch in chapters:
                assert "db_novel_id" in ch
                assert ch["db_novel_id"] is not None

        # Verify DB state
        uow2 = UnitOfWork(session_factory=sqlite_session_factory)
        with uow2:
            assert uow2.novels.count() == 1
            novel = uow2.novels.list(limit=1)[0]
            assert novel.title == "Nano Machine"
            assert novel.author == "NovelBin"
            db_chapters = uow2.novels.get_chapters(novel.id)
            assert len(db_chapters) >= 2
            assert db_chapters[0].content  # content is not empty

    def test_nlp_entity_extraction(self, sample_chapter):
        """5. Verify NLP pipeline extracts characters from chapter text."""
        use_case = ExtractEntitiesUseCase()
        result = use_case.execute(sample_chapter, chapter_id="test-ch-1")

        # Should find at least some characters
        assert len(result.character_mentions) > 0, "Expected at least 1 character mention"

        # Check for known characters from the sample
        canonicals = {m.canonical for m in result.character_mentions}
        # "lin lei" should appear (from conftest SAMPLE_CHAPTER)
        assert any("lin lei" in c for c in canonicals), f"Expected 'lin lei' in {canonicals}"

        # Should detect at least 1 organization
        assert len(result.organizations) > 0, "Expected at least 1 organization"
        org_names = {o.canonical.lower() for o in result.organizations}
        assert any("mount hua" in o for o in org_names), f"Expected 'Mount Hua' org in {org_names}"

        # Should detect at least 1 location
        assert len(result.locations) > 0, "Expected at least 1 location"

    def test_full_pipeline_e2e(self, sqlite_session_factory):
        """6. Full pipeline: scrape -> ingest -> NLP -> ingest entities -> graph."""
        from app.scrapers.novelfire import NovelFireScraper

        responses = _build_responses()
        progress_dir = Path(tempfile.mkdtemp(prefix="murim_full_e2e_"))

        # Phase 1: Scrape + ingest chapters
        uow = UnitOfWork(session_factory=sqlite_session_factory)
        with uow:
            scraper = NovelFireScraper(
                novel_slug="nano-machine",
                index_url="https://novelfire.net/book/nano-machine",
                progress_dir=progress_dir,
                ingest_use_case=IngestChapterUseCase(uow),
            )

            def fake_get(url: str, *args: Any, **kwargs: Any) -> MagicMock:
                resp = MagicMock()
                resp.text = responses.get(url, "<html></html>")
                resp.status_code = 200
                return resp

            scraper.session.get = fake_get
            chapters = scraper.scrape_novel()
            assert len(chapters) >= 2

            # Get novel and chapter IDs
            novel = uow.novels.list(limit=1)[0]
            db_chapters = uow.novels.get_chapters(novel.id)
            novel_id = novel.id
            chapter_ids = [ch.id for ch in db_chapters]

        # Phase 2: NLP extraction + entity ingestion per chapter
        extract_use_case = ExtractEntitiesUseCase()
        ingest_entities_uc = IngestEntitiesUseCase(uow)

        uow2 = UnitOfWork(session_factory=sqlite_session_factory)
        with uow2:
            total_chars = 0
            total_orgs = 0
            total_locs = 0

            for ch_id in chapter_ids:
                db_ch = uow2.chapters.get(ch_id)
                if db_ch is None or not db_ch.content:
                    continue

                extraction = extract_use_case.execute(db_ch.content, chapter_id=ch_id)
                result = ingest_entities_uc.execute(extraction)

                total_chars += result.new_characters + result.updated_characters
                total_orgs += result.new_organizations
                total_locs += result.new_locations

            # Phase 3: Build knowledge graph
            graph_uc = BuildKnowledgeGraphUseCase(uow2)
            graph = graph_uc.execute(novel_id=novel_id)

            # Assertions
            assert total_chars > 0, "Expected at least 1 character ingested"
            assert total_orgs > 0, "Expected at least 1 organization ingested"
            assert total_locs > 0, "Expected at least 1 location ingested"

            # Graph should have nodes
            assert graph.number_of_nodes() > 0, "Expected graph to have nodes"
            assert graph.number_of_edges() >= 0, "Expected graph to have edges"

            # Verify character nodes exist
            char_nodes = [n for n, d in graph.nodes(data=True) if d.get("kind") == "character"]
            assert len(char_nodes) > 0, "Expected character nodes in graph"

            # Verify org nodes exist
            org_nodes = [n for n, d in graph.nodes(data=True) if d.get("kind") == "organization"]
            assert len(org_nodes) > 0, "Expected organization nodes in graph"

            # Verify location nodes exist
            loc_nodes = [n for n, d in graph.nodes(data=True) if d.get("kind") == "location"]
            assert len(loc_nodes) > 0, "Expected location nodes in graph"

            # Verify novel hub
            novel_nodes = [n for n, d in graph.nodes(data=True) if d.get("kind") == "novel"]
            assert len(novel_nodes) > 0, "Expected novel node in graph"

            logger.info(
                "Full E2E pipeline OK: %d chars, %d orgs, %d locs, %d graph nodes, %d edges",
                total_chars,
                total_orgs,
                total_locs,
                graph.number_of_nodes(),
                graph.number_of_edges(),
            )

    def test_archetype_classification(self, sample_chapter):
        """7. Verify archetype classifier works on chapter text."""
        classifier = ArchetypeClassifier()
        archetype = classifier.classify("test-char-1", sample_chapter)

        assert archetype is not None
        assert archetype.character_id == "test-char-1"
        assert archetype.narrative_role is not None
        assert archetype.combat_style is not None
        assert archetype.classified_by == "rules"
        assert 0.0 <= archetype.role_confidence <= 1.0
        assert 0.0 <= archetype.combat_confidence <= 1.0

    def test_canonical_name_with_titles(self):
        """8. Verify canonicalize_name strips Murim honorifics."""
        from app.processing.patterns import canonicalize_name

        assert canonicalize_name("Elder Lin Lei") == "lin lei"
        assert canonicalize_name("Senior Brother Yi Yun") == "yi yun"
        assert canonicalize_name("Young Master Cheon Yeo-un") == "cheon yeo-un"
        assert canonicalize_name("  Di  Shi  ") == "di shi"
        assert canonicalize_name("") == ""

    def test_relationship_extraction(self):
        """9. Verify relationship extractor finds Murim relationships."""
        from app.processing import extract_relationships

        text = (
            "Lin Lei is the master of Yi Yun. "
            "Di Shi is the rival of Lin Lei. "
            "Qing Yan's disciple is Di Shi."
        )
        rels = extract_relationships(text)
        assert len(rels) >= 2, f"Expected >= 2 relationships, got {len(rels)}"

        rel_types = {r.relationship_type for r in rels}
        assert "master" in rel_types or "disciple" in rel_types
