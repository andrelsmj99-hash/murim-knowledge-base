"""
Domain entities — pure dataclasses independent of the persistence layer.
"""
from .archetype import CharacterArchetype, CombatStyle, NarrativeRole, PersonalityTrait
from .character import Alias, Character
from .character import Relationship as CharacterRelationship
from .location import Location
from .novel import Chapter, Novel
from .organization import Organization, OrganizationRelationship

__all__ = [
    "Alias",
    "Character",
    "CharacterArchetype",
    "CharacterRelationship",
    "Chapter",
    "CombatStyle",
    "NarrativeRole",
    "Novel",
    "Location",
    "Organization",
    "OrganizationRelationship",
    "PersonalityTrait",
]
