"""
Tests for batch_ingest and cross-novel deduplication.
"""

from __future__ import annotations

from app.core.unit_of_work import UnitOfWork
from app.core.use_cases.extract_entities import ChapterExtraction
from app.core.use_cases.ingest_entities import IngestEntitiesUseCase
from app.processing import CharacterMention


class TestCrossNovelDeduplication:
    """Characters with the same name in different novels must NOT merge."""

    def test_same_name_different_novels_get_separate_records(self, api_client):
        client, session_factory = api_client

        # Create two novels
        r1 = client.post("/api/v1/novels", json={"title": "Novel A", "author": "Author A"})
        novel_a_id = r1.json()["id"]
        r2 = client.post("/api/v1/novels", json={"title": "Novel B", "author": "Author B"})
        novel_b_id = r2.json()["id"]

        # Ingest character "Lin Lei" into novel A
        with UnitOfWork(session_factory=session_factory) as uow:
            uc = IngestEntitiesUseCase(uow)
            extraction_a = ChapterExtraction(
                character_mentions=[
                    CharacterMention(surface="Lin Lei", canonical="lin lei", start=0, end=7)
                ]
            )
            result_a = uc.execute(extraction_a, novel_id=novel_a_id)
            assert result_a.new_characters >= 1

        # Ingest same-named character into novel B
        with UnitOfWork(session_factory=session_factory) as uow:
            uc = IngestEntitiesUseCase(uow)
            extraction_b = ChapterExtraction(
                character_mentions=[
                    CharacterMention(surface="Lin Lei", canonical="lin lei", start=0, end=7)
                ]
            )
            result_b = uc.execute(extraction_b, novel_id=novel_b_id)
            assert result_b.new_characters >= 1

        # Verify: two separate character records exist
        from sqlalchemy import select

        from app.models.character import Character as CharacterORM

        with UnitOfWork(session_factory=session_factory) as uow:
            stmt = select(CharacterORM).where(CharacterORM.canonical_name == "lin lei")
            chars = uow.session.execute(stmt).scalars().all()
            assert len(chars) == 2
            novel_ids = {str(c.novel_id) for c in chars}
            assert novel_a_id in novel_ids
            assert novel_b_id in novel_ids

    def test_same_novel_same_name_merges(self, api_client):
        client, session_factory = api_client

        r = client.post("/api/v1/novels", json={"title": "Novel C", "author": "Author C"})
        novel_id = r.json()["id"]

        # Ingest same character twice in same novel
        with UnitOfWork(session_factory=session_factory) as uow:
            uc = IngestEntitiesUseCase(uow)
            extraction = ChapterExtraction(
                character_mentions=[
                    CharacterMention(surface="Lin Lei", canonical="lin lei", start=0, end=7)
                ]
            )
            result1 = uc.execute(extraction, novel_id=novel_id)
            assert result1.new_characters >= 1

        with UnitOfWork(session_factory=session_factory) as uow:
            uc = IngestEntitiesUseCase(uow)
            extraction = ChapterExtraction(
                character_mentions=[
                    CharacterMention(surface="Lin Lei", canonical="lin lei", start=0, end=7)
                ]
            )
            result2 = uc.execute(extraction, novel_id=novel_id)
            # Should update, not create new
            assert result2.new_characters == 0
            assert result2.updated_characters >= 1

        # Verify: only one character record
        from sqlalchemy import select

        from app.models.character import Character as CharacterORM

        with UnitOfWork(session_factory=session_factory) as uow:
            stmt = select(CharacterORM).where(CharacterORM.canonical_name == "lin lei")
            chars = uow.session.execute(stmt).scalars().all()
            assert len(chars) == 1


class TestBatchIngestResume:
    """Verify resume logic works correctly."""

    def test_novel_stats_endpoint_returns_correct_data(self, api_client):
        client, _ = api_client
        r = client.post(
            "/api/v1/novels",
            json={"title": "Resume Test", "author": "Author", "language": "en"},
        )
        novel_id = r.json()["id"]

        # Add 3 chapters
        for n in range(1, 4):
            client.post(
                f"/api/v1/novels/{novel_id}/chapters",
                json={"chapter_number": n, "content": f"Chapter {n} content. " * 30},
            )

        # Check stats
        r = client.get(f"/api/v1/novels/{novel_id}/stats")
        assert r.status_code == 200
        stats = r.json()
        assert stats["chapters"] == 3
        assert stats["novel_id"] == novel_id
        assert stats["title"] == "Resume Test"
