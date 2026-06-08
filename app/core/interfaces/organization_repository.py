"""
Organization repository contract.
"""
from __future__ import annotations

import abc

from app.core.entities import Character, Organization
from app.core.interfaces.repository import IRepository


class IOrganizationRepository(IRepository[Organization], abc.ABC):
    """Persistence operations for :class:`Organization` aggregates."""

    @abc.abstractmethod
    def get_by_name_type(self, name: str, type: str) -> Organization | None:
        """Find an organization by its unique (name, type) key."""

    @abc.abstractmethod
    def upsert(self, organization: Organization) -> Organization:
        """Insert or return the existing organization by canonical key."""

    @abc.abstractmethod
    def get_rivals(self, org_id: str) -> list[Organization]:
        """Return organizations marked as rivals of the given one."""

    @abc.abstractmethod
    def get_allies(self, org_id: str) -> list[Organization]:
        """Return organizations marked as allies of the given one."""

    @abc.abstractmethod
    def search_by_name(self, query: str, *, limit: int = 20) -> list[Organization]:
        """Substring / case-insensitive search by name."""

    @abc.abstractmethod
    def get_members(self, org_id: str) -> list[Character]:
        """Return all characters who are members of this organization."""

    @abc.abstractmethod
    def add_relationship(
        self, organization_id: str, related_organization_id: str, relationship_type: str
    ) -> bool:
        """Create a relationship between two organizations. Returns False if already exists."""
