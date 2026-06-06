"""
Character models for the knowledge base.
"""
import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Table, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


# ---------------------------------------------------------------------------
# Association tables (many-to-many)
# ---------------------------------------------------------------------------

character_locations = Table(
    "character_locations",
    Base.metadata,
    Column("character_id", UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True),
    Column("location_id", UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True),
)

character_organizations = Table(
    "character_organizations",
    Base.metadata,
    Column("character_id", UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True),
    Column("organization_id", UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True),
    Column("role", String(100), nullable=True),  # e.g., "Sect Leader", "Elder", "Disciple"
)


# ---------------------------------------------------------------------------
# Character ↔ Character relationships
# ---------------------------------------------------------------------------

class Relationship(Base):
    __tablename__ = "relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id = Column(UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    related_character_id = Column(UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(100), nullable=False)  # e.g., "master", "disciple", "rival", "ally"

    character = relationship("Character", foreign_keys=[character_id], back_populates="relationships")
    related_character = relationship("Character", foreign_keys=[related_character_id], back_populates="related_to")

    __table_args__ = (
        UniqueConstraint("character_id", "related_character_id", "relationship_type", name="uix_relationship"),
    )


# ---------------------------------------------------------------------------
# Character
# ---------------------------------------------------------------------------

class Character(Base):
    __tablename__ = "characters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), index=True, nullable=False)
    canonical_name = Column(String(255), index=True, nullable=False)  # Normalized for dedup
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
    organizations = relationship("Organization", secondary=character_organizations, back_populates="members")

    # Embedding for semantic search (JSON-serialized float vector)
    embedding = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("canonical_name", name="uix_canonical_name"),
    )


# ---------------------------------------------------------------------------
# Alias / Title
# ---------------------------------------------------------------------------

class Alias(Base):
    __tablename__ = "aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id = Column(UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    alias_type = Column(String(100), nullable=False)  # "Alias", "Nickname", "Demon Name"
    alias_value = Column(String(255), index=True, nullable=False)

    character = relationship("Character", back_populates="aliases")

    __table_args__ = (UniqueConstraint("character_id", "alias_value", name="uix_character_alias"),)


class Title(Base):
    __tablename__ = "titles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id = Column(UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), index=True, nullable=False)

    character = relationship("Character", back_populates="titles")

    __table_args__ = (UniqueConstraint("character_id", "title", name="uix_character_title"),)
