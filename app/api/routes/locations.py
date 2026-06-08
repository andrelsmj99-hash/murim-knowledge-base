"""
/locations routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_uow
from app.api.schemas import (
    LocationCreate,
    LocationRead,
    Page,
    PageMeta,
)
from app.core.entities import Location
from app.core.unit_of_work import UnitOfWork

router = APIRouter()


def _to_read(loc) -> LocationRead:
    return LocationRead(
        id=loc.id,
        name=loc.name,
        type=loc.type,
        description=loc.description,
        region=loc.region,
        realm=loc.realm,
        parent_location_id=loc.parent_location_id,
        sub_location_ids=list(loc.sub_location_ids),
        character_ids=list(loc.character_ids),
        organization_ids=list(loc.organization_ids),
    )


@router.get("", response_model=Page)
def list_locations(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    uow: UnitOfWork = Depends(get_uow),
) -> Page:
    repo = uow.locations
    items = [_to_read(loc) for loc in repo.list(limit=limit, offset=offset)]
    return Page(items=items, meta=PageMeta(total=repo.count(), limit=limit, offset=offset))


@router.get("/{location_id}", response_model=LocationRead)
def get_location(location_id: str, uow: UnitOfWork = Depends(get_uow)) -> LocationRead:
    loc = uow.locations.get(location_id)
    if loc is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return _to_read(loc)


@router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
def create_location(payload: LocationCreate, uow: UnitOfWork = Depends(get_uow)) -> LocationRead:
    existing = uow.locations.get_by_name_type(payload.name, payload.type)
    if existing is not None:
        return _to_read(existing)
    loc = Location(
        name=payload.name,
        type=payload.type,
        description=payload.description,
        region=payload.region,
        realm=payload.realm,
        parent_location_id=payload.parent_location_id,
    )
    created = uow.locations.add(loc)
    uow.commit()
    return _to_read(created)


@router.get("/{location_id}/sub-locations", response_model=list[LocationRead])
def list_sub_locations(location_id: str, uow: UnitOfWork = Depends(get_uow)) -> list[LocationRead]:
    if uow.locations.get(location_id) is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return [_to_read(loc) for loc in uow.locations.get_sub_locations(location_id)]
