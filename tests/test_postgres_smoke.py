"""
PostgreSQL smoke tests — skipped automatically when DATABASE_URL is not Postgres.

These tests validate:
1. pgvector extension is active
2. HNSW index exists on characters.embedding_vec
3. embedding_vec column is of type vector(384)
4. Character count exceeds expected minimum (>5000 after production migration)

Run against live Postgres:
    DATABASE_URL=postgresql://murim_user:murim_password@localhost:5432/murim_db \
        pytest tests/test_postgres_smoke.py -v

CI: these tests are SKIPPED unless DATABASE_URL points to Postgres — safe to include
in the standard pytest run without a Postgres service.
"""

from __future__ import annotations

import os

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, text


def _is_postgres() -> bool:
    url = os.environ.get("DATABASE_URL", "")
    return "postgresql" in url or "postgres" in url


@pytest.fixture(scope="module")
def pg_engine():
    url = os.environ.get("DATABASE_URL", "")
    engine = create_engine(url)
    yield engine
    engine.dispose()


# ── Skip marker applied to all tests in this module ──────────────────────────

pytestmark = pytest.mark.skipif(
    not _is_postgres(),
    reason="DATABASE_URL does not point to PostgreSQL — skipping Postgres smoke tests",
)


class TestPgvectorExtension:
    def test_vector_extension_active(self, pg_engine: sa.Engine) -> None:
        with pg_engine.connect() as conn:
            row = conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            ).fetchone()
        assert row is not None, "pgvector extension is not installed in the database"
        assert row[0] == "vector"

    def test_vector_extension_version(self, pg_engine: sa.Engine) -> None:
        with pg_engine.connect() as conn:
            row = conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            ).fetchone()
        assert row is not None
        # pgvector 0.5+ is required for HNSW index support
        major, minor = (int(x) for x in row[0].split(".")[:2])
        assert (major, minor) >= (0, 5), f"pgvector {row[0]} < 0.5 — HNSW not supported"


class TestSchemaCorrectness:
    def test_all_tables_exist(self, pg_engine: sa.Engine) -> None:
        expected_tables = {
            "novels",
            "chapters",
            "characters",
            "aliases",
            "titles",
            "relationships",
            "locations",
            "organizations",
            "organization_relationships",
            "character_locations",
            "character_organizations",
        }
        with pg_engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                )
            ).fetchall()
        actual_tables = {row[0] for row in rows} - {"alembic_version"}
        missing = expected_tables - actual_tables
        assert not missing, f"Missing tables: {missing}"

    def test_embedding_vec_is_vector_type(self, pg_engine: sa.Engine) -> None:
        with pg_engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT udt_name FROM information_schema.columns "
                    "WHERE table_name = 'characters' AND column_name = 'embedding_vec'"
                )
            ).fetchone()
        assert row is not None, "embedding_vec column not found in characters table"
        assert row[0] == "vector", (
            f"embedding_vec has type '{row[0]}', expected 'vector' (pgvector)"
        )

    def test_hnsw_index_exists(self, pg_engine: sa.Engine) -> None:
        with pg_engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename = 'characters' "
                    "AND indexname = 'idx_characters_embedding_vec_hnsw'"
                )
            ).fetchone()
        assert row is not None, (
            "HNSW index 'idx_characters_embedding_vec_hnsw' not found on characters table"
        )

    def test_novel_id_on_characters(self, pg_engine: sa.Engine) -> None:
        """Characters should have novel_id for cross-novel dedup."""
        with pg_engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'characters' AND column_name = 'novel_id'"
                )
            ).fetchone()
        assert row is not None, "novel_id column missing from characters table"


class TestDataPopulation:
    def test_novels_populated(self, pg_engine: sa.Engine) -> None:
        with pg_engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM novels")).scalar()
        assert count >= 5, f"Expected ≥5 novels, found {count} — run migration script"

    def test_chapters_populated(self, pg_engine: sa.Engine) -> None:
        with pg_engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM chapters")).scalar()
        assert count >= 1680, f"Expected ≥1680 chapters, found {count} — run migration script"

    def test_characters_populated(self, pg_engine: sa.Engine) -> None:
        with pg_engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM characters")).scalar()
        assert count >= 5000, f"Expected ≥5000 characters, found {count} — run migration script"

    def test_embeddings_coverage(self, pg_engine: sa.Engine) -> None:
        with pg_engine.connect() as conn:
            total = conn.execute(text("SELECT COUNT(*) FROM characters")).scalar()
            embedded = conn.execute(
                text("SELECT COUNT(*) FROM characters WHERE embedding_vec IS NOT NULL")
            ).scalar()
        if total == 0:
            pytest.skip("No characters in database — run migration first")
        coverage = embedded / total
        assert coverage >= 0.95, (
            f"Only {embedded}/{total} characters ({coverage:.1%}) have embeddings — "
            "run scripts/batch_embed.py"
        )

    def test_archetypes_coverage(self, pg_engine: sa.Engine) -> None:
        with pg_engine.connect() as conn:
            total = conn.execute(text("SELECT COUNT(*) FROM characters")).scalar()
            classified = conn.execute(
                text("SELECT COUNT(*) FROM characters WHERE archetype IS NOT NULL")
            ).scalar()
        if total == 0:
            pytest.skip("No characters in database — run migration first")
        coverage = classified / total
        assert coverage >= 0.95, (
            f"Only {classified}/{total} characters ({coverage:.1%}) have archetypes — "
            "run scripts/batch_classify.py"
        )


class TestSemanticSearch:
    def test_vector_similarity_query(self, pg_engine: sa.Engine) -> None:
        """Verify pgvector similarity query executes against real data."""
        with pg_engine.connect() as conn:
            has_embedded = conn.execute(
                text("SELECT COUNT(*) FROM characters WHERE embedding_vec IS NOT NULL")
            ).scalar()

        if has_embedded == 0:
            pytest.skip("No embedded characters — run scripts/batch_embed.py first")

        # Build a zero-vector query to test the index works (not semantic quality)
        zero_vec = "[" + ",".join(["0.0"] * 384) + "]"
        with pg_engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT id, name, embedding_vec <=> '{zero_vec}'::vector AS dist "  # noqa: S608
                    "FROM characters WHERE embedding_vec IS NOT NULL "
                    "ORDER BY dist LIMIT 5"
                )
            ).fetchall()
        assert len(rows) > 0, "HNSW query returned no results"
        assert all(row[2] is not None for row in rows), "Distance values should not be NULL"
