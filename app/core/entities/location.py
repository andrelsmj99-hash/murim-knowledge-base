"""
Domain entity for a Location.
"""
from __future__ import annotations

import uuid as uuid_module
from dataclasses import dataclass, field


@dataclass
class Location:
    """A geographic or in-world place (city, sect grounds, mountain, kingdom, …)."""

    id: str = field(default_factory=lambda: str(uuid_module.uuid4()))
    name: str = ""
    type: str = ""  # e.g. "City", "Mountain", "Sect Grounds", "Kingdom"
    description: str | None = None
    region: str | None = None
    realm: str | None = None
    parent_location_id: str | None = None
    sub_location_ids: list[str] = field(default_factory=list)
    character_ids: list[str] = field(default_factory=list)
    organization_ids: list[str] = field(default_factory=list)

    @property
    def canonical_key(self) -> tuple[str, str]:
        return (self.name.strip().lower(), self.type.strip().lower())
