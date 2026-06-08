"""
Models package — exposes ORM entities and base machinery.
"""

from .base import Base, SessionLocal, engine, get_db
from .character import (
    Alias,
    Character,
    Relationship,
    Title,
    character_locations,
    character_organizations,
)
from .location import Location
from .novel import Chapter, Novel
from .organization import Organization, OrganizationRelationship

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "Character",
    "Alias",
    "Title",
    "Relationship",
    "Location",
    "Organization",
    "OrganizationRelationship",
    "Novel",
    "Chapter",
    "character_locations",
    "character_organizations",
]
