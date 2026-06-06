"""
Organization repository contract.
"""
from __future__ import annotations

import abc
from typing import List, Optional

from app.core.entities import Character, Organization
from app.core.interfaces.repository import IRepository


class IOrganizationRepository(IRepository[Organization], abc.ABC):
    """Persistence operations for :class:`Organization` aggregates."""

    @abc.abstractmethod
    def get_by_name_type(self, name: str, type: str) -> Optional[Organization]:
        """Find an organization by its unique (name, type) key."""

    @abc.abstractmethod
    def upsert(self, organization: Organization) -> Organization:
        """Insert or return the existing organization by canonical key."""

    @abc.abstractmethod
    def get_rivals(self, org_id: str) -> List[Organization]:
        """Return organizations marked as rivals of the given one."""

    @abc.abstractmethod
    def get_allies(self, org_id: str) -> List[Organization]:
        """Return organizations marked as allies of the given one."""

    @abc.abstractmethod
    def search_by_name(self, query: str, *, limit: int = 20) -> List[Organization]:
        """Substring / case-insensitive search by name."""

    @abc.abstractmethod
    def get_members(self, org_id: str) -> List[Character]:
        """Return all characters who are members of this organization."""
