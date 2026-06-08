"""fix embedding_vec column type for pgvector

Revision ID: d2e3f4a5b6c7
Revises: c1a2b3c4d5e6
Create Date: 2026-06-08 00:00:00.000000

"""

from collections.abc import Sequence
from contextlib import suppress

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2e3f4a5b6c7"
down_revision: str | None = "c1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # On PostgreSQL with pgvector, alter embedding_vec from Text to vector(384).
    # On SQLite this is a no-op (pgvector is not available).
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        with suppress(Exception):
            # pgvector extension not installed — column stays as Text,
            # the ORM's EmbeddingVector type handles the fallback.
            op.execute("ALTER TABLE characters ALTER COLUMN embedding_vec TYPE vector(384)")


def downgrade() -> None:
    pass
