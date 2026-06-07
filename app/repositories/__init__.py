"""
SQLAlchemy adapters that implement the domain repository contracts.
"""
from .chapter_repository import ChapterRepository
from .character_repository import CharacterRepository
from .location_repository import LocationRepository
from .novel_repository import NovelRepository
from .organization_repository import OrganizationRepository

__all__ = [
    "ChapterRepository",
    "CharacterRepository",
    "NovelRepository",
    "OrganizationRepository",
    "LocationRepository",
]
