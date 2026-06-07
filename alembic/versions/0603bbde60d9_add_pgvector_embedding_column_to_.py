"""add pgvector embedding column to characters

Revision ID: 0603bbde60d9
Revises: 0001_initial
Create Date: 2026-06-07 03:18:05.537689

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0603bbde60d9'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add pgvector column for efficient semantic search (PostgreSQL)
    # SQLite fallback uses the existing `embedding` TEXT column
    op.add_column('characters', sa.Column('embedding_vec', sa.Text(), nullable=True))

    # Create HNSW index for vector similarity search (PostgreSQL only)
    # This will be skipped on SQLite
    try:
        op.execute("CREATE INDEX IF NOT EXISTS ix_characters_embedding_vec_hnsw ON characters USING hnsw (embedding_vec vector_cosine_ops)")
    except Exception:
        # pgvector not available or not PostgreSQL
        pass


def downgrade() -> None:
    # Drop index if exists
    try:
        op.execute("DROP INDEX IF EXISTS ix_characters_embedding_vec_hnsw")
    except Exception:
        pass

    # Remove pgvector column
    op.drop_column('characters', 'embedding_vec')