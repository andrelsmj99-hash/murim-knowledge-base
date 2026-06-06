"""
Models package — exposes ORM entities and base machinery.
"""
from .base import Base, engine, SessionLocal, get_db
from .character import (
    Character,
    Alias,
    Title,
    Relationship,
    character_locations,
    character_organizations,
)
from .location import Location
from .organization import Organization, OrganizationRelationship
from .novel import Novel, Chapter

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
