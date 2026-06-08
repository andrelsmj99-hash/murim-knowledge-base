"""
/organizations and /organizations/{id}/{rivals,allies,relationships} routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_uow
from app.api.schemas import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationRelationshipCreate,
    Page,
    PageMeta,
)
from app.core.entities import Organization
from app.core.unit_of_work import UnitOfWork

router = APIRouter()


def _to_read(o) -> OrganizationRead:
    return OrganizationRead(
        id=o.id,
        name=o.name,
        type=o.type,
        description=o.description,
        parent_org_id=o.parent_org_id,
        headquarters_id=o.headquarters_id,
        subsidiary_ids=list(o.subsidiary_ids),
        member_ids=list(o.member_ids),
        rival_ids=list(o.relationships.get("rival", [])),
        ally_ids=list(o.relationships.get("ally", [])),
    )


@router.get("", response_model=Page)
def list_organizations(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    uow: UnitOfWork = Depends(get_uow),
) -> Page:
    repo = uow.organizations
    items = [_to_read(o) for o in repo.list(limit=limit, offset=offset)]
    return Page(items=items, meta=PageMeta(total=repo.count(), limit=limit, offset=offset))


@router.get("/{org_id}", response_model=OrganizationRead)
def get_organization(org_id: str, uow: UnitOfWork = Depends(get_uow)) -> OrganizationRead:
    o = uow.organizations.get(org_id)
    if o is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return _to_read(o)


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate, uow: UnitOfWork = Depends(get_uow)
) -> OrganizationRead:
    existing = uow.organizations.get_by_name_type(payload.name, payload.type)
    if existing is not None:
        return _to_read(existing)
    org = Organization(
        name=payload.name,
        type=payload.type,
        description=payload.description,
    )
    created = uow.organizations.add(org)
    uow.commit()
    return _to_read(created)


@router.get("/{org_id}/rivals", response_model=list[OrganizationRead])
def list_rivals(org_id: str, uow: UnitOfWork = Depends(get_uow)) -> list[OrganizationRead]:
    if uow.organizations.get(org_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return [_to_read(o) for o in uow.organizations.get_rivals(org_id)]


@router.get("/{org_id}/allies", response_model=list[OrganizationRead])
def list_allies(org_id: str, uow: UnitOfWork = Depends(get_uow)) -> list[OrganizationRead]:
    if uow.organizations.get(org_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return [_to_read(o) for o in uow.organizations.get_allies(org_id)]


@router.post(
    "/{org_id}/relationships",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
)
def add_relationship(
    org_id: str,
    payload: OrganizationRelationshipCreate,
    uow: UnitOfWork = Depends(get_uow),
) -> OrganizationRead:
    if uow.organizations.get(org_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if uow.organizations.get(payload.related_organization_id) is None:
        raise HTTPException(status_code=404, detail="Related organization not found")
    uow.organizations.add_relationship(
        org_id, payload.related_organization_id, payload.relationship_type
    )
    uow.commit()
    return _to_read(uow.organizations.get(org_id))
