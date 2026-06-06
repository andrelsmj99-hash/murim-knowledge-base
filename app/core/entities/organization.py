"""
Domain entities for Organizations and their inter-org relationships.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import uuid as uuid_module


@dataclass
class OrganizationRelationship:
    """Directional relationship between two organizations."""

    source_id: str
    target_id: str
    relationship_type: str  # "rival", "ally", "subordinate", "parent"
    confidence: float = 1.0


@dataclass
class Organization:
    """A sect, clan, guild, alliance or cult."""

    id: str = field(default_factory=lambda: str(uuid_module.uuid4()))
    name: str = ""
    type: str = ""  # "Sect", "Clan", "Guild", "Alliance", "Cult"
    description: Optional[str] = None

    parent_org_id: Optional[str] = None
    subsidiary_ids: List[str] = field(default_factory=list)
    headquarters_id: Optional[str] = None
    member_ids: List[str] = field(default_factory=list)

    # Grouped by relationship_type
    relationships: Dict[str, List[str]] = field(default_factory=dict)

    def add_relationship(self, target_id: str, relationship_type: str) -> None:
        bucket = self.relationships.setdefault(relationship_type, [])
        if target_id not in bucket:
            bucket.append(target_id)

    @property
    def canonical_key(self) -> tuple[str, str]:
        return (self.name.strip().lower(), self.type.strip().lower())
