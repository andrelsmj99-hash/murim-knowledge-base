"""add HNSW index for pgvector cosine search

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-06-09 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3f4a5b6c7d8"
down_revision: str | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create HNSW index on embedding_vec for efficient cosine similarity search.
    # Uses SAVEPOINT to isolate failures (e.g. pgvector not installed, or column still Text).
    # On SQLite this is a no-op.
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text("SAVEPOINT create_hnsw_index"))
        try:
            conn.execute(
                sa.text(
                    "CREATE INDEX IF NOT EXISTS idx_characters_embedding_vec_hnsw "
                    "ON characters USING hnsw (embedding_vec vector_cosine_ops) "
                    "WITH (m = 16, ef_construction = 64)"
                )
            )
            conn.execute(sa.text("RELEASE SAVEPOINT create_hnsw_index"))
        except Exception:
            conn.execute(sa.text("ROLLBACK TO SAVEPOINT create_hnsw_index"))


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text("SAVEPOINT drop_hnsw_index"))
        try:
            conn.execute(sa.text("DROP INDEX IF EXISTS idx_characters_embedding_vec_hnsw"))
            conn.execute(sa.text("RELEASE SAVEPOINT drop_hnsw_index"))
        except Exception:
            conn.execute(sa.text("ROLLBACK TO SAVEPOINT drop_hnsw_index"))
