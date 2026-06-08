"""
Domain entities for the Character concept.
"""

from __future__ import annotations

import uuid as uuid_module
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.entities.archetype import CharacterArchetype


@dataclass
class Alias:
    alias_type: str  # e.g., "Title", "Nickname", "Demon Name"
    value: str
    canonical_value: str  # Normalized value for deduplication


@dataclass
class Character:
    id: str = field(default_factory=lambda: str(uuid_module.uuid4()))
    name: str = ""
    canonical_name: str = ""  # Normalized for deduplication and linking
    aliases: list[Alias] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    epithets: list[str] = field(default_factory=list)
    gender: str | None = None
    description: str | None = None
    first_appearance: str | None = None  # e.g., "Volume 1, Chapter 5"
    appearance_frequency: int = 0
    organizations: list[str] = field(default_factory=list)  # IDs of organizations
    locations: list[str] = field(default_factory=list)  # IDs of locations
    relationships: dict[str, list[str]] = field(
        default_factory=dict
    )  # relationship_type -> [character_ids]
    embedding: str | None = None  # JSON-serialized float vector for semantic search
    archetype: CharacterArchetype | None = None  # Character archetype classification object

    def add_alias(self, alias_type: str, value: str):
        """Add an alias to the character."""
        if not any(a.value == value for a in self.aliases):
            self.aliases.append(
                Alias(
                    alias_type=alias_type,
                    value=value,
                    canonical_value=value.lower().replace(" ", "_"),
                )
            )

    def increment_frequency(self):
        """Increment the appearance frequency."""
        self.appearance_frequency += 1


@dataclass
class Relationship:
    source_id: str
    target_id: str
    relationship_type: str  # "master", "disciple", "rival", "ally", "parent", "child"
    confidence: float = 1.0
