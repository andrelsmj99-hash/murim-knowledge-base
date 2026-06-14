"""add novel_id to characters for cross-novel deduplication

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-06-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4a5b6c7d8e9"
down_revision: str | None = "e3f4a5b6c7d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add novel_id FK to characters (nullable — existing rows remain valid).
    op.add_column(
        "characters",
        sa.Column("novel_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_characters_novel_id",
        "characters",
        "novels",
        ["novel_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Drop the old single-column unique constraint on canonical_name and replace with
    # the composite (canonical_name, novel_id) constraint added in session 32.
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text("ALTER TABLE characters DROP CONSTRAINT IF EXISTS uix_canonical_name"))
    elif conn.dialect.name == "sqlite":
        # SQLite does not support DROP CONSTRAINT; the constraint is dropped implicitly
        # when recreating the table — which Alembic does not do here, so we leave it.
        pass

    op.create_unique_constraint(
        "uix_canonical_name_novel",
        "characters",
        ["canonical_name", "novel_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uix_canonical_name_novel", "characters", type_="unique")
    op.drop_constraint("fk_characters_novel_id", "characters", type_="foreignkey")
    op.drop_column("characters", "novel_id")
    op.create_unique_constraint("uix_canonical_name", "characters", ["canonical_name"])
