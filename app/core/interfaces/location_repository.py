"""
Location repository contract.
"""

from __future__ import annotations

import abc

from app.core.entities import Character, Location
from app.core.interfaces.repository import IRepository


class ILocationRepository(IRepository[Location], abc.ABC):
    """Persistence operations for :class:`Location` aggregates."""

    @abc.abstractmethod
    def get_by_name_type(self, name: str, type: str) -> Location | None:
        """Find a location by its unique (name, type) key."""

    @abc.abstractmethod
    def upsert(self, location: Location) -> Location:
        """Insert or return the existing location by canonical key."""

    @abc.abstractmethod
    def search_by_name(self, query: str, *, limit: int = 20) -> list[Location]:
        """Substring / case-insensitive search by name."""

    @abc.abstractmethod
    def get_sub_locations(self, location_id: str) -> list[Location]:
        """Return the direct children of a location in the hierarchy."""

    @abc.abstractmethod
    def get_characters(self, location_id: str) -> list[Character]:
        """Return all characters associated with this location."""
