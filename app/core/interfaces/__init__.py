"""
Domain-layer repository contracts (ports).

These interfaces are independent of any persistence technology. Concrete
adapters live under :mod:`app.repositories`.
"""
from .chapter_repository import IChapterRepository
from .character_repository import ICharacterRepository
from .location_repository import ILocationRepository
from .novel_repository import INovelRepository
from .organization_repository import IOrganizationRepository
from .repository import IRepository

__all__ = [
    "IRepository",
    "IChapterRepository",
    "ICharacterRepository",
    "INovelRepository",
    "IOrganizationRepository",
    "ILocationRepository",
]
