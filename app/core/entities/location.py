"""
Domain entity for a Location.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import uuid as uuid_module


@dataclass
class Location:
    """A geographic or in-world place (city, sect grounds, mountain, kingdom, …)."""

    id: str = field(default_factory=lambda: str(uuid_module.uuid4()))
    name: str = ""
    type: str = ""  # e.g. "City", "Mountain", "Sect Grounds", "Kingdom"
    description: Optional[str] = None
    region: Optional[str] = None
    realm: Optional[str] = None
    parent_location_id: Optional[str] = None
    sub_location_ids: List[str] = field(default_factory=list)
    character_ids: List[str] = field(default_factory=list)
    organization_ids: List[str] = field(default_factory=list)

    @property
    def canonical_key(self) -> tuple[str, str]:
        return (self.name.strip().lower(), self.type.strip().lower())
