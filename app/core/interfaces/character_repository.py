"""
Character repository contract.
"""
from __future__ import annotations

import abc

from app.core.entities import Character
from app.core.interfaces.repository import IRepository


class ICharacterRepository(IRepository[Character], abc.ABC):
    """Persistence operations for :class:`Character` aggregates."""

    @abc.abstractmethod
    def get_by_canonical_name(self, canonical_name: str) -> Character | None:
        """Look up a character by its deduplication key."""

    @abc.abstractmethod
    def get_by_alias(self, alias_value: str) -> Character | None:
        """Resolve a character from any of its alias strings."""

    @abc.abstractmethod
    def search_by_name(self, query: str, *, limit: int = 20) -> list[Character]:
        """Substring / case-insensitive search by name or canonical name."""

    @abc.abstractmethod
    def upsert_by_canonical_name(self, character: Character) -> Character:
        """Return an existing character matched by ``canonical_name`` or add it."""

    @abc.abstractmethod
    def update(self, character_id: str, *, name: str | None = None, gender: str | None = None, description: str | None = None, first_appearance: str | None = None) -> Character | None:
        """Partial update of a character's scalar fields. Returns updated entity or None if not found."""

    @abc.abstractmethod
    def add_alias(self, character_id: str, alias_type: str, alias_value: str) -> bool:
        """Add an alias to a character. Returns True if created, False if character not found."""

    @abc.abstractmethod
    def add_title(self, character_id: str, title: str) -> bool:
        """Add a title to a character. Returns True if created, False if character not found."""

    @abc.abstractmethod
    def set_embedding(self, character_id: str, embedding: str) -> None:
        """Persist a JSON-serialized embedding vector for a character."""

    @abc.abstractmethod
    def link_location(self, character_id: str, location_id: str) -> bool:
        """Associate a character with a location. Returns True if linked, False if character/location not found."""

    @abc.abstractmethod
    def unlink_location(self, character_id: str, location_id: str) -> bool:
        """Remove a character-location association. Returns True if unlinked, False if not found."""

    @abc.abstractmethod
    def link_organization(self, character_id: str, organization_id: str, role: str | None = None) -> bool:
        """Associate a character with an organization. Returns True if linked, False if not found."""

    @abc.abstractmethod
    def unlink_organization(self, character_id: str, organization_id: str) -> bool:
        """Remove a character-organization association. Returns True if unlinked, False if not found."""

    @abc.abstractmethod
    def add_relationship(
        self, character_id: str, related_character_id: str, relationship_type: str
    ) -> bool:
        """Add a relationship between two characters. Returns True if created, False if character(s) not found or duplicate."""

    @abc.abstractmethod
    def get_relationships(self, character_id: str) -> dict[str, list[str]]:
        """Return all relationships for a character, grouped by relationship_type."""

    @abc.abstractmethod
    def remove_relationship(
        self, character_id: str, related_character_id: str, relationship_type: str
    ) -> bool:
        """Remove a specific relationship. Returns True if removed, False if not found."""

    @abc.abstractmethod
    def search_by_embedding(
        self, query_vec: list[float], *, limit: int = 20
    ) -> list[Character]:
        """
        Search characters by vector similarity.
        Uses pgvector HNSW index when available (PostgreSQL), falls back to in-Python cosine.
        Returns characters with `_similarity` attribute set (0.0-1.0).
        """

    @abc.abstractmethod
    def set_archetype(self, character_id: str, archetype) -> bool:
        """Persist a CharacterArchetype for a character. Returns True if successful."""
