"""
/characters and /characters/{id}/relationships routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_encoder, get_uow
from app.api.schemas import (
    AliasCreate,
    AliasRead,
    ArchetypeResponse,
    CharacterCreate,
    CharacterLocationLink,
    CharacterOrganizationLink,
    CharacterRead,
    CharacterRelationshipCreate,
    CharacterUpdate,
    ClassifyAllResponse,
    Page,
    PageMeta,
    TitleCreate,
)
from app.core.entities import Character
from app.core.interfaces import ICharacterRepository
from app.core.unit_of_work import UnitOfWork
from app.core.use_cases import (
    ClassifyAllCharacters,
    ClassifyCharacterArchetype,
    GenerateEmbeddingsUseCase,
)
from app.nlp.archetype_classifier import ArchetypeClassifier

router = APIRouter()


def _to_read(c) -> CharacterRead:
    return CharacterRead(
        id=c.id,
        name=c.name,
        canonical_name=c.canonical_name,
        gender=c.gender,
        description=c.description,
        first_appearance=c.first_appearance,
        appearance_frequency=c.appearance_frequency or 0,
        aliases=[AliasRead(alias_type=a.alias_type, alias_value=a.value) for a in c.aliases],
        titles=list(c.titles),
        organizations=list(c.organizations),
        locations=list(c.locations),
        relationships={k: list(v) for k, v in c.relationships.items()},
        has_embedding=bool(getattr(c, "embedding", None)),
    )


@router.get("", response_model=Page)
def list_characters(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    uow: UnitOfWork = Depends(get_uow),
) -> Page:
    repo: ICharacterRepository = uow.characters
    items = [_to_read(c) for c in repo.list(limit=limit, offset=offset)]
    return Page(items=items, meta=PageMeta(total=repo.count(), limit=limit, offset=offset))


@router.get("/{character_id}", response_model=CharacterRead)
def get_character(character_id: str, uow: UnitOfWork = Depends(get_uow)) -> CharacterRead:
    c = uow.characters.get(character_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return _to_read(c)


@router.post("", response_model=CharacterRead, status_code=status.HTTP_201_CREATED)
def create_character(payload: CharacterCreate, uow: UnitOfWork = Depends(get_uow)) -> CharacterRead:
    canonical = (payload.canonical_name or payload.name).strip().lower()
    canonical = " ".join(canonical.split())
    existing = uow.characters.get_by_canonical_name(canonical)
    if existing is not None:
        return _to_read(existing)
    character = Character(
        name=payload.name.strip(),
        canonical_name=canonical,
        gender=payload.gender,
        description=payload.description,
        first_appearance=payload.first_appearance,
    )
    created = uow.characters.add(character)
    uow.commit()
    return _to_read(created)


@router.patch("/{character_id}", response_model=CharacterRead)
def update_character(
    character_id: str,
    payload: CharacterUpdate,
    uow: UnitOfWork = Depends(get_uow),
) -> CharacterRead:
    updated = uow.characters.update(
        character_id,
        name=payload.name,
        gender=payload.gender,
        description=payload.description,
        first_appearance=payload.first_appearance,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Character not found")
    uow.commit()
    return _to_read(updated)


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_character(character_id: str, uow: UnitOfWork = Depends(get_uow)) -> None:
    if not uow.characters.delete(character_id):
        raise HTTPException(status_code=404, detail="Character not found")
    uow.commit()


@router.post("/{character_id}/embed", response_model=CharacterRead)
def embed_character(
    character_id: str,
    uow: UnitOfWork = Depends(get_uow),
    encoder=Depends(get_encoder),
) -> CharacterRead:
    uc = GenerateEmbeddingsUseCase(uow, encoder=encoder.encode)
    result = uc.execute(character_id)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error or "Character not found")
    return _to_read(uow.characters.get(character_id))


@router.post("/embed-all", response_model=dict)
def embed_all_characters(
    force: bool = Query(False, description="Regenerate embeddings for all characters"),
    uow: UnitOfWork = Depends(get_uow),
    encoder=Depends(get_encoder),
) -> dict:
    uc = GenerateEmbeddingsUseCase(uow, encoder=encoder.encode)
    result = uc.execute_all(force=force)
    return {
        "total": len(result.results),
        "success": result.success_count,
        "failures": result.failure_count,
    }


@router.post(
    "/{character_id}/aliases",
    response_model=AliasRead,
    status_code=status.HTTP_201_CREATED,
)
def add_alias(
    character_id: str,
    payload: AliasCreate,
    uow: UnitOfWork = Depends(get_uow),
) -> AliasRead:
    if not uow.characters.add_alias(character_id, payload.alias_type, payload.alias_value):
        raise HTTPException(status_code=404, detail="Character not found")
    uow.commit()
    return AliasRead(alias_type=payload.alias_type, alias_value=payload.alias_value)


@router.post(
    "/{character_id}/titles",
    response_model=CharacterRead,
    status_code=status.HTTP_201_CREATED,
)
def add_title(
    character_id: str,
    payload: TitleCreate,
    uow: UnitOfWork = Depends(get_uow),
) -> CharacterRead:
    if not uow.characters.add_title(character_id, payload.title):
        raise HTTPException(status_code=404, detail="Character not found")
    uow.commit()
    return _to_read(uow.characters.get(character_id))


@router.post(
    "/{character_id}/relationships",
    response_model=CharacterRead,
    status_code=status.HTTP_201_CREATED,
)
def add_relationship(
    character_id: str,
    payload: CharacterRelationshipCreate,
    uow: UnitOfWork = Depends(get_uow),
) -> CharacterRead:
    if uow.characters.get(character_id) is None:
        raise HTTPException(status_code=404, detail="Character not found")
    if uow.characters.get(payload.related_character_id) is None:
        raise HTTPException(status_code=404, detail="Related character not found")
    if character_id == payload.related_character_id:
        raise HTTPException(status_code=400, detail="Cannot relate a character to itself")
    if not uow.characters.add_relationship(
        character_id, payload.related_character_id, payload.relationship_type
    ):
        raise HTTPException(status_code=409, detail="Relationship already exists")
    uow.commit()
    return _to_read(uow.characters.get(character_id))


@router.post(
    "/{character_id}/locations",
    response_model=CharacterRead,
    status_code=status.HTTP_201_CREATED,
)
def link_character_location(
    character_id: str,
    payload: CharacterLocationLink,
    uow: UnitOfWork = Depends(get_uow),
) -> CharacterRead:
    if not uow.characters.link_location(character_id, payload.location_id):
        raise HTTPException(status_code=404, detail="Character or location not found")
    uow.commit()
    return _to_read(uow.characters.get(character_id))


@router.delete(
    "/{character_id}/locations/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unlink_character_location(
    character_id: str,
    location_id: str,
    uow: UnitOfWork = Depends(get_uow),
) -> None:
    if not uow.characters.unlink_location(character_id, location_id):
        raise HTTPException(status_code=404, detail="Character-location link not found")
    uow.commit()


@router.post(
    "/{character_id}/organizations",
    response_model=CharacterRead,
    status_code=status.HTTP_201_CREATED,
)
def link_character_organization(
    character_id: str,
    payload: CharacterOrganizationLink,
    uow: UnitOfWork = Depends(get_uow),
) -> CharacterRead:
    if not uow.characters.link_organization(character_id, payload.organization_id):
        raise HTTPException(status_code=404, detail="Character or organization not found")
    uow.commit()
    return _to_read(uow.characters.get(character_id))


@router.delete(
    "/{character_id}/organizations/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unlink_character_organization(
    character_id: str,
    organization_id: str,
    uow: UnitOfWork = Depends(get_uow),
) -> None:
    if not uow.characters.unlink_organization(character_id, organization_id):
        raise HTTPException(status_code=404, detail="Character-organization link not found")
    uow.commit()


# ---------------------------------------------------------------------------
# Archetype classification
# ---------------------------------------------------------------------------


@router.post("/{character_id}/classify", response_model=ArchetypeResponse)
def classify_character_archetype(
    character_id: str,
    uow: UnitOfWork = Depends(get_uow),
) -> ArchetypeResponse:
    """Classify a character's archetype based on all chapters where they appear."""
    character = uow.characters.get(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    uc = ClassifyCharacterArchetype(
        character_repository=uow.characters,
        chapter_repository=uow.chapters,
        classifier=ArchetypeClassifier(),
    )
    archetype = uc.execute(character_id)
    return ArchetypeResponse(
        character_id=archetype.character_id,
        narrative_role=archetype.narrative_role.value,
        combat_style=archetype.combat_style.value,
        personality_traits=[t.value for t in archetype.personality_traits],
        role_confidence=archetype.role_confidence,
        combat_confidence=archetype.combat_confidence,
        trait_scores=archetype.trait_scores,
        classified_by=archetype.classified_by,
    )


@router.get("/{character_id}/archetype", response_model=ArchetypeResponse | None)
def get_character_archetype(
    character_id: str,
    uow: UnitOfWork = Depends(get_uow),
) -> ArchetypeResponse | None:
    """Get a character's previously classified archetype."""
    character = uow.characters.get(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    if character.archetype is None:
        return None
    archetype = character.archetype
    return ArchetypeResponse(
        character_id=archetype.character_id,
        narrative_role=archetype.narrative_role.value,
        combat_style=archetype.combat_style.value,
        personality_traits=[t.value for t in archetype.personality_traits],
        role_confidence=archetype.role_confidence,
        combat_confidence=archetype.combat_confidence,
        trait_scores=archetype.trait_scores,
        classified_by=archetype.classified_by,
    )


@router.post("/classify-all", response_model=ClassifyAllResponse)
def classify_all_characters(
    uow: UnitOfWork = Depends(get_uow),
) -> ClassifyAllResponse:
    """Classify all characters' archetypes in batch."""
    uc = ClassifyAllCharacters(
        character_repository=uow.characters,
        chapter_repository=uow.chapters,
        classifier=ArchetypeClassifier(),
    )
    results = uc.execute()
    uow.commit()
    return ClassifyAllResponse(
        total=len(results),
        classified=len(results),
    )
