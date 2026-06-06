"""
Domain-layer repository contracts (ports).

These interfaces are independent of any persistence technology. Concrete
adapters live under :mod:`app.repositories`.
"""
from .repository import IRepository
from .character_repository import ICharacterRepository
from .novel_repository import INovelRepository
from .organization_repository import IOrganizationRepository
from .location_repository import ILocationRepository

__all__ = [
    "IRepository",
    "ICharacterRepository",
    "INovelRepository",
    "IOrganizationRepository",
    "ILocationRepository",
]
