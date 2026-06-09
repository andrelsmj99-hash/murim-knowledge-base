"""add HNSW index for pgvector cosine search

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-06-09 00:00:00.000000

"""

from collections.abc import Sequence
from contextlib import suppress

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3f4a5b6c7d8"
down_revision: str | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create HNSW index for efficient cosine similarity search on pgvector.
    # On SQLite this is a no-op (pgvector is not available).
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        with suppress(Exception):
            # HNSW index for O(log n) approximate nearest neighbor search
            # using cosine distance operator (<=>)
            op.execute(
                "CREATE INDEX IF NOT EXISTS idx_characters_embedding_hnsw "
                "ON characters USING hnsw (embedding vector_cosine_ops) "
                "WITH (m = 16, ef_construction = 64)"
            )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        with suppress(Exception):
            op.execute("DROP INDEX IF EXISTS idx_characters_embedding_hnsw")
