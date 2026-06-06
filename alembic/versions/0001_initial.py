"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-06

Creates the full Murim Knowledge Base schema:
  novels, chapters, characters, aliases, titles, relationships,
  locations, organizations, organization_relationships,
  character_locations (assoc), character_organizations (assoc).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ novels
    op.create_table(
        "novels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("genre", sa.String(100), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("language", sa.String(10), nullable=True, server_default="en"),
        sa.Column("total_chapters", sa.Integer(), nullable=True, server_default="0"),
        sa.UniqueConstraint("title", "author", name="uix_novel_title_author"),
    )
    op.create_index("ix_novels_title", "novels", ["title"])

    # ---------------------------------------------------------------- chapters
    op.create_table(
        "chapters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("novel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("novels.id"), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=True, server_default="0"),
        sa.UniqueConstraint("novel_id", "chapter_number", name="uix_chapter_novel_number"),
    )

    # -------------------------------------------------------------- characters
    op.create_table(
        "characters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("canonical_name", sa.String(255), nullable=False),
        sa.Column("gender", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("first_appearance", sa.String(255), nullable=True),
        sa.Column("appearance_frequency", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.UniqueConstraint("canonical_name", name="uix_canonical_name"),
    )
    op.create_index("ix_characters_name", "characters", ["name"])
    op.create_index("ix_characters_canonical_name", "characters", ["canonical_name"])

    # --------------------------------------------------------------- locations
    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("region", sa.String(255), nullable=True),
        sa.Column("realm", sa.String(255), nullable=True),
        sa.Column("parent_location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=True),
        sa.UniqueConstraint("name", "type", name="uix_location_name_type"),
    )
    op.create_index("ix_locations_name", "locations", ["name"])

    # ----------------------------------------------------------- organizations
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("headquarters_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=True),
        sa.UniqueConstraint("name", "type", name="uix_org_name_type"),
    )
    op.create_index("ix_organizations_name", "organizations", ["name"])

    # ----------------------------------------------------------------- aliases
    op.create_table(
        "aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias_type", sa.String(100), nullable=False),
        sa.Column("alias_value", sa.String(255), nullable=False),
        sa.UniqueConstraint("character_id", "alias_value", name="uix_character_alias"),
    )
    op.create_index("ix_aliases_alias_value", "aliases", ["alias_value"])

    # ------------------------------------------------------------------ titles
    op.create_table(
        "titles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.UniqueConstraint("character_id", "title", name="uix_character_title"),
    )
    op.create_index("ix_titles_title", "titles", ["title"])

    # ----------------------------------------------------------- relationships
    op.create_table(
        "relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "related_character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(100), nullable=False),
        sa.UniqueConstraint(
            "character_id", "related_character_id", "relationship_type", name="uix_relationship"
        ),
    )

    # ---------------------------------------------- organization_relationships
    op.create_table(
        "organization_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "related_organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(100), nullable=False),
        sa.UniqueConstraint(
            "organization_id",
            "related_organization_id",
            "relationship_type",
            name="uix_org_relationship",
        ),
    )

    # --------------------------------------- character_locations (association)
    op.create_table(
        "character_locations",
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    # ----------------------------------- character_organizations (association)
    op.create_table(
        "character_organizations",
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("character_organizations")
    op.drop_table("character_locations")
    op.drop_table("organization_relationships")
    op.drop_table("relationships")
    op.drop_index("ix_titles_title", table_name="titles")
    op.drop_table("titles")
    op.drop_index("ix_aliases_alias_value", table_name="aliases")
    op.drop_table("aliases")
    op.drop_index("ix_organizations_name", table_name="organizations")
    op.drop_table("organizations")
    op.drop_index("ix_locations_name", table_name="locations")
    op.drop_table("locations")
    op.drop_index("ix_characters_canonical_name", table_name="characters")
    op.drop_index("ix_characters_name", table_name="characters")
    op.drop_table("characters")
    op.drop_table("chapters")
    op.drop_index("ix_novels_title", table_name="novels")
    op.drop_table("novels")
