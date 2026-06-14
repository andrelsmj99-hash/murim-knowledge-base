"""fix embedding_vec column type for pgvector

Revision ID: d2e3f4a5b6c7
Revises: c1a2b3c4d5e6
Create Date: 2026-06-08 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2e3f4a5b6c7"
down_revision: str | None = "c1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # On PostgreSQL with pgvector, alter embedding_vec from Text to vector(384).
    # Uses SAVEPOINT to avoid aborting the enclosing transaction if the ALTER fails
    # (e.g. when the pgvector extension is not installed — column stays as Text).
    # On SQLite this is a no-op.
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text("SAVEPOINT alter_embedding_vec"))
        try:
            conn.execute(
                sa.text(
                    "ALTER TABLE characters ALTER COLUMN embedding_vec "
                    "TYPE vector(384) USING embedding_vec::vector"
                )
            )
            conn.execute(sa.text("RELEASE SAVEPOINT alter_embedding_vec"))
        except Exception:
            conn.execute(sa.text("ROLLBACK TO SAVEPOINT alter_embedding_vec"))


def downgrade() -> None:
    pass
