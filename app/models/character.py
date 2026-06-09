"""
Character models for the knowledge base.
"""

import uuid

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base

# pgvector is optional - only used with PostgreSQL
try:
    from pgvector.sqlalchemy import Vector as PgVector

    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    PgVector = None


class EmbeddingVector(TypeDecorator):
    """
    Custom type that uses pgvector.Vector on PostgreSQL and Text on SQLite.
    Stores embeddings as JSON arrays of floats.
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and PGVECTOR_AVAILABLE:
            return dialect.type_descriptor(PgVector(384))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        # Value is already a JSON string from the repository
        return value

    def process_result_value(self, value, dialect):
        return value


# ---------------------------------------------------------------------------
# Association tables (many-to-many)
# ---------------------------------------------------------------------------

character_locations = Table(
    "character_locations",
    Base.metadata,
    Column(
        "character_id",
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "location_id",
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

character_organizations = Table(
    "character_organizations",
    Base.metadata,
    Column(
        "character_id",
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "organization_id",
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("role", String(100), nullable=True),  # e.g., "Sect Leader", "Elder", "Disciple"
)


# ---------------------------------------------------------------------------
# Character ↔ Character relationships
# ---------------------------------------------------------------------------


class Relationship(Base):
    __tablename__ = "relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id = Column(
        UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    related_character_id = Column(
        UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type = Column(
        String(100), nullable=False
    )  # e.g., "master", "disciple", "rival", "ally"

    character = relationship(
        "Character", foreign_keys=[character_id], back_populates="relationships"
    )
    related_character = relationship(
        "Character", foreign_keys=[related_character_id], back_populates="related_to"
    )

    __table_args__ = (
        UniqueConstraint(
            "character_id", "related_character_id", "relationship_type", name="uix_relationship"
        ),
    )


# ---------------------------------------------------------------------------
# Character
# ---------------------------------------------------------------------------


class Character(Base):
    __tablename__ = "characters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), index=True, nullable=False)
    canonical_name = Column(String(255), index=True, nullable=False)  # Normalized for dedup
    novel_id = Column(
        UUID(as_uuid=True), ForeignKey("novels.id", ondelete="SET NULL"), nullable=True
    )
    gender = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    first_appearance = Column(String(255), nullable=True)  # e.g., "Volume 1, Chapter 5"
    appearance_frequency = Column(Integer, default=0)

    # One-to-many
    aliases = relationship("Alias", back_populates="character", cascade="all, delete-orphan")
    titles = relationship("Title", back_populates="character", cascade="all, delete-orphan")

    # Self-referential many-to-many (via Relationship row)
    relationships = relationship(
        "Relationship",
        foreign_keys=[Relationship.character_id],
        back_populates="character",
        cascade="all, delete-orphan",
    )
    related_to = relationship(
        "Relationship",
        foreign_keys=[Relationship.related_character_id],
        back_populates="related_character",
        cascade="all, delete-orphan",
    )

    # Many-to-many
    locations = relationship("Location", secondary=character_locations, back_populates="characters")
    organizations = relationship(
        "Organization", secondary=character_organizations, back_populates="members"
    )

    # Embedding for semantic search (JSON-serialized float vector)
    # Uses pgvector.Vector on PostgreSQL, Text on SQLite
    embedding_vec = Column(EmbeddingVector, nullable=True)
    # Legacy text column for backward compatibility (JSON string)
    embedding = Column(Text, nullable=True)
    # Character archetype classification (JSON-serialized)
    archetype = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("canonical_name", "novel_id", name="uix_canonical_name_novel"),
    )


# ---------------------------------------------------------------------------
# Alias / Title
# ---------------------------------------------------------------------------


class Alias(Base):
    __tablename__ = "aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id = Column(
        UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    alias_type = Column(String(100), nullable=False)  # "Alias", "Nickname", "Demon Name"
    alias_value = Column(String(255), index=True, nullable=False)

    character = relationship("Character", back_populates="aliases")

    __table_args__ = (UniqueConstraint("character_id", "alias_value", name="uix_character_alias"),)


class Title(Base):
    __tablename__ = "titles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id = Column(
        UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(255), index=True, nullable=False)

    character = relationship("Character", back_populates="titles")

    __table_args__ = (UniqueConstraint("character_id", "title", name="uix_character_title"),)
