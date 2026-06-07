"""
Abstract base for all repositories.

A repository owns a SQLAlchemy session and exposes entity-oriented
operations. Repositories are not thread-safe and are intended to be
instantiated per Unit-of-Work.
"""
from __future__ import annotations

import abc
import builtins
from collections.abc import Iterable
from typing import TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


class IRepository[T](abc.ABC):
    """Generic CRUD contract shared by all repositories."""

    #: Class-level marker so subclasses can reference their entity type.
    entity_cls: type

    def __init__(self, session: Session) -> None:
        self.session = session

    # --- read operations -------------------------------------------------

    @abc.abstractmethod
    def get(self, entity_id: str) -> T | None:
        """Return a single entity by its primary key, or ``None``."""

    @abc.abstractmethod
    def list(self, *, limit: int = 100, offset: int = 0) -> builtins.list[T]:
        """Return a paginated list of entities."""

    @abc.abstractmethod
    def count(self) -> int:
        """Return the total number of entities in the repository."""

    # --- write operations ------------------------------------------------

    @abc.abstractmethod
    def add(self, entity: T) -> T:
        """Add a new entity to the session (does not commit)."""

    def add_many(self, entities: Iterable[T]) -> builtins.list[T]:
        """Bulk-add entities. Default implementation calls ``add`` for each."""
        return [self.add(e) for e in entities]

    @abc.abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete an entity by id. Returns ``True`` if something was removed."""

    def commit(self) -> None:
        """Commit the current transaction."""
        self.session.commit()

    def rollback(self) -> None:
        """Roll back the current transaction."""
        self.session.rollback()
