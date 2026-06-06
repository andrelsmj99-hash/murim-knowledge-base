"""
Location repository contract.
"""
from __future__ import annotations

import abc
from typing import List, Optional

from app.core.entities import Character, Location
from app.core.interfaces.repository import IRepository


class ILocationRepository(IRepository[Location], abc.ABC):
    """Persistence operations for :class:`Location` aggregates."""

    @abc.abstractmethod
    def get_by_name_type(self, name: str, type: str) -> Optional[Location]:
        """Find a location by its unique (name, type) key."""

    @abc.abstractmethod
    def upsert(self, location: Location) -> Location:
        """Insert or return the existing location by canonical key."""

    @abc.abstractmethod
    def search_by_name(self, query: str, *, limit: int = 20) -> List[Location]:
        """Substring / case-insensitive search by name."""

    @abc.abstractmethod
    def get_sub_locations(self, location_id: str) -> List[Location]:
        """Return the direct children of a location in the hierarchy."""

    @abc.abstractmethod
    def get_characters(self, location_id: str) -> List[Character]:
        """Return all characters associated with this location."""
