"""
Domain entities — pure dataclasses independent of the persistence layer.
"""
from .character import Alias, Character
from .character import Relationship as CharacterRelationship
from .location import Location
from .novel import Chapter, Novel
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
