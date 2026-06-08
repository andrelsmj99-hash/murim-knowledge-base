"""
SQLAlchemy implementation of :class:`ILocationRepository`.
"""

from __future__ import annotations

import builtins
import uuid as uuid_module

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.entities import Character, Location
from app.core.interfaces import ILocationRepository
from app.models.location import Location as LocationORM


def _to_uuid(value: str) -> uuid_module.UUID:
    return uuid_module.UUID(str(value))


def _to_entity(orm: LocationORM) -> Location:
    return Location(
        id=str(orm.id),
        name=orm.name,
        type=orm.type,
        description=orm.description,
        region=orm.region,
        realm=orm.realm,
        parent_location_id=str(orm.parent_location_id) if orm.parent_location_id else None,
        sub_location_ids=[str(s.id) for s in orm.sub_locations],
        character_ids=[str(c.id) for c in orm.characters],
        organization_ids=[str(o.id) for o in orm.organizations],
    )


def _to_orm(entity: Location) -> LocationORM:
    return LocationORM(
        id=_to_uuid(entity.id),
        name=entity.name,
        type=entity.type,
        description=entity.description,
        region=entity.region,
        realm=entity.realm,
        parent_location_id=_to_uuid(entity.parent_location_id)
        if entity.parent_location_id
        else None,
    )


class LocationRepository(ILocationRepository):
    entity_cls = Location

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    # --- read -----------------------------------------------------------

    def get(self, entity_id: str) -> Location | None:
        orm = self.session.get(LocationORM, _to_uuid(entity_id))
        return _to_entity(orm) if orm else None

    def list(self, *, limit: int = 100, offset: int = 0) -> builtins.list[Location]:
        stmt = select(LocationORM).order_by(LocationORM.name).limit(limit).offset(offset)
        return [_to_entity(loc) for loc in self.session.execute(stmt).scalars().all()]

    def count(self) -> int:
        return int(self.session.scalar(select(func.count(LocationORM.id))) or 0)

    def get_by_name_type(self, name: str, type: str) -> Location | None:
        stmt = select(LocationORM).where(LocationORM.name == name, LocationORM.type == type)
        orm = self.session.execute(stmt).scalar_one_or_none()
        return _to_entity(orm) if orm else None

    def search_by_name(self, query: str, *, limit: int = 20) -> builtins.list[Location]:
        if not query:
            return []
        pattern = f"%{query.lower()}%"
        stmt = (
            select(LocationORM)
            .where(
                or_(
                    LocationORM.name.ilike(pattern),
                    LocationORM.region.ilike(pattern),
                    LocationORM.realm.ilike(pattern),
                )
            )
            .order_by(LocationORM.name)
            .limit(limit)
        )
        return [_to_entity(loc) for loc in self.session.execute(stmt).scalars().all()]

    def get_sub_locations(self, location_id: str) -> builtins.list[Location]:
        stmt = (
            select(LocationORM)
            .where(LocationORM.parent_location_id == _to_uuid(location_id))
            .order_by(LocationORM.name)
        )
        return [_to_entity(loc) for loc in self.session.execute(stmt).scalars().all()]

    def get_characters(self, location_id: str) -> builtins.list[Character]:
        from app.models.character import Character as CharacterORM
        from app.repositories.character_repository import _to_entity as _char_to_entity

        stmt = (
            select(CharacterORM)
            .join(CharacterORM.locations)
            .where(LocationORM.id == _to_uuid(location_id))
        )
        return [_char_to_entity(c) for c in self.session.execute(stmt).scalars().all()]

    # --- write ----------------------------------------------------------

    def add(self, entity: Location) -> Location:
        orm = _to_orm(entity)
        self.session.add(orm)
        self.session.flush()
        return _to_entity(orm)

    def delete(self, entity_id: str) -> bool:
        orm = self.session.get(LocationORM, _to_uuid(entity_id))
        if orm is None:
            return False
        self.session.delete(orm)
        self.session.flush()
        return True

    def upsert(self, location: Location) -> Location:
        existing = self.get_by_name_type(location.name, location.type)
        if existing:
            orm = self.session.get(LocationORM, _to_uuid(existing.id))
            assert orm is not None, f"LocationORM {existing.id} disappeared after get_by_name_type"
            orm.description = location.description or orm.description
            orm.region = location.region or orm.region
            orm.realm = location.realm or orm.realm
            orm.parent_location_id = (
                _to_uuid(location.parent_location_id)
                if location.parent_location_id
                else orm.parent_location_id
            )
            self.session.flush()
            return _to_entity(orm)
        return self.add(location)
