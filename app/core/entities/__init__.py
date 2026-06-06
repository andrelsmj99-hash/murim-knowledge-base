"""
Domain entities — pure dataclasses independent of the persistence layer.
"""
from .character import Alias, Character, Relationship as CharacterRelationship
from .novel import Chapter, Novel
from .location import Location
from .organization import Organization, OrganizationRelationship

__all__ = [
    "Alias",
    "Character",
    "CharacterRelationship",
    "Chapter",
    "Novel",
    "Location",
    "Organization",
    "OrganizationRelationship",
]
