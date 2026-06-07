"""
Unit of Work — owns a SQLAlchemy session and exposes all repositories.

Use cases receive a ``UnitOfWork`` instead of individual repositories, which
keeps session/transaction management centralized.
"""
from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from app.core.interfaces import (
    IChapterRepository,
    ICharacterRepository,
    ILocationRepository,
    INovelRepository,
    IOrganizationRepository,
)
from app.models import SessionLocal
from app.repositories import (
    ChapterRepository,
    CharacterRepository,
    LocationRepository,
    NovelRepository,
    OrganizationRepository,
)


class UnitOfWork:
    """
    Concrete UoW that lazily instantiates repositories on first access
    and exposes :meth:`commit` / :meth:`rollback` helpers.

    Usable as a context manager::

        with UnitOfWork() as uow:
            uow.novels.add_chapter(chapter)
            uow.commit()
    """

    session: Session

    def __init__(self, session_factory: sessionmaker | None = None) -> None:
        self._session_factory = session_factory or SessionLocal
        self._characters: ICharacterRepository | None = None
        self._chapters: IChapterRepository | None = None
        self._novels: INovelRepository | None = None
        self._organizations: IOrganizationRepository | None = None
        self._locations: ILocationRepository | None = None

    # --- context manager -------------------------------------------------

    def __enter__(self) -> UnitOfWork:
        self.session = self._session_factory()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is not None:
                self.rollback()
        finally:
            self.session.close()

    # --- repository accessors -------------------------------------------

    @property
    def characters(self) -> ICharacterRepository:
        if self._characters is None:
            self._characters = CharacterRepository(self.session)
        return self._characters

    @property
    def chapters(self) -> IChapterRepository:
        if self._chapters is None:
            self._chapters = ChapterRepository(self.session)
        return self._chapters

    @property
    def novels(self) -> INovelRepository:
        if self._novels is None:
            self._novels = NovelRepository(self.session)
        return self._novels

    @property
    def organizations(self) -> IOrganizationRepository:
        if self._organizations is None:
            self._organizations = OrganizationRepository(self.session)
        return self._organizations

    @property
    def locations(self) -> ILocationRepository:
        if self._locations is None:
            self._locations = LocationRepository(self.session)
        return self._locations

    # --- transaction control --------------------------------------------

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def flush(self) -> None:
        self.session.flush()
