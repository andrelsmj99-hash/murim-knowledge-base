"""
Domain entities for the Character concept.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
import uuid as uuid_module

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
    aliases: List[Alias] = field(default_factory=list)
    titles: List[str] = field(default_factory=list)
    epithets: List[str] = field(default_factory=list)
    gender: Optional[str] = None
    description: Optional[str] = None
    first_appearance: Optional[str] = None  # e.g., "Volume 1, Chapter 5"
    appearance_frequency: int = 0
    organizations: List[str] = field(default_factory=list)  # IDs of organizations
    locations: List[str] = field(default_factory=list)  # IDs of locations
    relationships: Dict[str, List[str]] = field(default_factory=dict)  # relationship_type -> [character_ids]
    embedding: Optional[str] = None  # JSON-serialized float vector for semantic search
    
    def add_alias(self, alias_type: str, value: str):
        """Add an alias to the character."""
        if not any(a.value == value for a in self.aliases):
            self.aliases.append(Alias(alias_type=alias_type, value=value, canonical_value=value.lower().replace(" ", "_")))

    def increment_frequency(self):
        """Increment the appearance frequency."""
        self.appearance_frequency += 1

@dataclass
class Relationship:
    source_id: str
    target_id: str
    relationship_type: str  # "master", "disciple", "rival", "ally", "parent", "child"
    confidence: float = 1.0