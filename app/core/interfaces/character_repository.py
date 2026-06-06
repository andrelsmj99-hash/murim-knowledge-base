"""
Character repository contract.
"""
from __future__ import annotations

import abc
from typing import List, Optional

from app.core.entities import Character
from app.core.interfaces.repository import IRepository


class ICharacterRepository(IRepository[Character], abc.ABC):
    """Persistence operations for :class:`Character` aggregates."""

    @abc.abstractmethod
    def get_by_canonical_name(self, canonical_name: str) -> Optional[Character]:
        """Look up a character by its deduplication key."""

    @abc.abstractmethod
    def get_by_alias(self, alias_value: str) -> Optional[Character]:
        """Resolve a character from any of its alias strings."""

    @abc.abstractmethod
    def search_by_name(self, query: str, *, limit: int = 20) -> List[Character]:
        """Substring / case-insensitive search by name or canonical name."""

    @abc.abstractmethod
    def upsert_by_canonical_name(self, character: Character) -> Character:
        """Return an existing character matched by ``canonical_name`` or add it."""

    @abc.abstractmethod
    def update(self, character_id: str, *, name: Optional[str] = None, gender: Optional[str] = None, description: Optional[str] = None, first_appearance: Optional[str] = None) -> Optional[Character]:
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
    def link_organization(self, character_id: str, organization_id: str, role: Optional[str] = None) -> bool:
        """Associate a character with an organization. Returns True if linked, False if not found."""

    @abc.abstractmethod
    def unlink_organization(self, character_id: str, organization_id: str) -> bool:
        """Remove a character-organization association. Returns True if unlinked, False if not found."""
