"""
SQLAlchemy adapters that implement the domain repository contracts.
"""
from .character_repository import CharacterRepository
from .novel_repository import NovelRepository
from .organization_repository import OrganizationRepository
from .location_repository import LocationRepository

__all__ = [
    "CharacterRepository",
    "NovelRepository",
    "OrganizationRepository",
    "LocationRepository",
]
