"""
SQLAlchemy implementation of :class:`IOrganizationRepository`.
"""
from __future__ import annotations

import builtins
import uuid as uuid_module

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.entities import Character, Organization
from app.core.interfaces import IOrganizationRepository
from app.models.organization import Organization as OrganizationORM
from app.models.organization import OrganizationRelationship as OrganizationRelationshipORM


def _to_uuid(value: str) -> uuid_module.UUID:
    return uuid_module.UUID(str(value))


def _to_entity(orm: OrganizationORM) -> Organization:
    return Organization(
        id=str(orm.id),
        name=orm.name,
        type=orm.type,
        description=orm.description,
        parent_org_id=str(orm.parent_org_id) if orm.parent_org_id else None,
        subsidiary_ids=[str(s.id) for s in orm.subsidiaries],
        headquarters_id=str(orm.headquarters_id) if orm.headquarters_id else None,
        member_ids=[str(m.id) for m in orm.members],
        relationships={},  # populated separately via OrganizationRelationship rows
    )


def _load_relationships(session: Session, org_id: str) -> dict[str, list[str]]:
    """Bucket related-organization ids by relationship_type for the given org."""
    rows = (
        session.query(OrganizationRelationshipORM)
        .filter(OrganizationRelationshipORM.organization_id == _to_uuid(org_id))
        .all()
    )
    out: dict[str, list[str]] = {}
    for row in rows:
        out.setdefault(row.relationship_type, []).append(str(row.related_organization_id))
    return out


def _to_orm(entity: Organization) -> OrganizationORM:
    return OrganizationORM(
        id=_to_uuid(entity.id),
        name=entity.name,
        type=entity.type,
        description=entity.description,
    )


class OrganizationRepository(IOrganizationRepository):
    entity_cls = Organization

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    # --- read -----------------------------------------------------------

    def get(self, entity_id: str) -> Organization | None:
        orm = self.session.get(OrganizationORM, _to_uuid(entity_id))
        if orm is None:
            return None
        ent = _to_entity(orm)
        ent.relationships = _load_relationships(self.session, ent.id)
        return ent

    def list(self, *, limit: int = 100, offset: int = 0) -> builtins.list[Organization]:
        stmt = select(OrganizationORM).order_by(OrganizationORM.name).limit(limit).offset(offset)
        out = []
        for orm in self.session.execute(stmt).scalars().all():
            ent = _to_entity(orm)
            ent.relationships = _load_relationships(self.session, ent.id)
            out.append(ent)
        return out

    def count(self) -> int:
        return int(self.session.scalar(select(func.count(OrganizationORM.id))) or 0)

    def get_by_name_type(self, name: str, type: str) -> Organization | None:
        stmt = select(OrganizationORM).where(
            OrganizationORM.name == name, OrganizationORM.type == type
        )
        orm = self.session.execute(stmt).scalar_one_or_none()
        if orm is None:
            return None
        ent = _to_entity(orm)
        ent.relationships = _load_relationships(self.session, ent.id)
        return ent

    def get_rivals(self, org_id: str) -> builtins.list[Organization]:
        stmt = (
            select(OrganizationORM)
            .join(
                OrganizationRelationshipORM,
                OrganizationRelationshipORM.related_organization_id == OrganizationORM.id,
            )
            .where(
                OrganizationRelationshipORM.organization_id == _to_uuid(org_id),
                OrganizationRelationshipORM.relationship_type == "rival",
            )
        )
        return [_to_entity(o) for o in self.session.execute(stmt).scalars().all()]

    def get_allies(self, org_id: str) -> builtins.list[Organization]:
        stmt = (
            select(OrganizationORM)
            .join(
                OrganizationRelationshipORM,
                OrganizationRelationshipORM.related_organization_id == OrganizationORM.id,
            )
            .where(
                OrganizationRelationshipORM.organization_id == _to_uuid(org_id),
                OrganizationRelationshipORM.relationship_type == "ally",
            )
        )
        return [_to_entity(o) for o in self.session.execute(stmt).scalars().all()]

    def search_by_name(self, query: str, *, limit: int = 20) -> builtins.list[Organization]:
        if not query:
            return []
        pattern = f"%{query.lower()}%"
        stmt = (
            select(OrganizationORM)
            .where(or_(OrganizationORM.name.ilike(pattern), OrganizationORM.type.ilike(pattern)))
            .order_by(OrganizationORM.name)
            .limit(limit)
        )
        return [_to_entity(o) for o in self.session.execute(stmt).scalars().all()]

    def get_members(self, org_id: str) -> builtins.list[Character]:
        from app.models.character import Character as CharacterORM
        from app.repositories.character_repository import _to_entity as _char_to_entity

        stmt = (
            select(CharacterORM)
            .join(CharacterORM.organizations)
            .where(OrganizationORM.id == _to_uuid(org_id))
        )
        return [_char_to_entity(c) for c in self.session.execute(stmt).scalars().all()]

    # --- write ----------------------------------------------------------

    def add(self, entity: Organization) -> Organization:
        orm = _to_orm(entity)
        self.session.add(orm)
        self.session.flush()
        return _to_entity(orm)

    def delete(self, entity_id: str) -> bool:
        orm = self.session.get(OrganizationORM, _to_uuid(entity_id))
        if orm is None:
            return False
        self.session.delete(orm)
        self.session.flush()
        return True

    def upsert(self, organization: Organization) -> Organization:
        existing = self.get_by_name_type(organization.name, organization.type)
        if existing:
            orm = self.session.get(OrganizationORM, _to_uuid(existing.id))
            orm.description = organization.description or orm.description
            self.session.flush()
            return _to_entity(orm)
        return self.add(organization)

    def add_relationship(
        self, organization_id: str, related_organization_id: str, relationship_type: str
    ) -> bool:
        existing = (
            self.session.query(OrganizationRelationshipORM)
            .filter_by(
                organization_id=_to_uuid(organization_id),
                related_organization_id=_to_uuid(related_organization_id),
                relationship_type=relationship_type,
            )
            .first()
        )
        if existing is not None:
            return False
        self.session.add(
            OrganizationRelationshipORM(
                organization_id=_to_uuid(organization_id),
                related_organization_id=_to_uuid(related_organization_id),
                relationship_type=relationship_type,
            )
        )
        self.session.flush()
        return True
