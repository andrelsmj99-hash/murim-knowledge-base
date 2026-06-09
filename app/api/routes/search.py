"""
Search routes.

Provides endpoints for:
- GET /search: Combined lexical + optional semantic search (backward-compatible)
- GET /search/semantic: Semantic search across characters
- GET /search/similar/{character_id}: Find similar characters
- GET /search/cross-novel: Search across all novels
"""

from __future__ import annotations

import logging
import math

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_encoder, get_uow
from app.api.schemas import (
    CharacterSimilarityHit,
    CharacterSimilarityResponse,
    SearchHit,
    SearchResponse,
    SemanticSearchHit,
    SemanticSearchResponse,
)
from app.core.unit_of_work import UnitOfWork
from app.core.use_cases.semantic_search import SemanticSearch

logger = logging.getLogger(__name__)

router = APIRouter()


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, description="Free-text query"),
    limit: int = Query(20, ge=1, le=200),
    semantic: bool = Query(True, description="Use embeddings when available"),
    uow: UnitOfWork = Depends(get_uow),
    encoder=Depends(get_encoder),
) -> SearchResponse:
    query_vec: list[float] | None = None
    if semantic:
        query_vec = encoder.encode(q)

    hits: list[SearchHit] = []
    q_lower = q.lower()

    if query_vec is not None:
        pgvector_hits = uow.characters.search_by_embedding(query_vec, limit=limit * 2)
        for c in pgvector_hits:
            score = getattr(c, "_similarity", 0.0)
            hits.append(SearchHit(id=c.id, name=c.name, kind="character", score=score))

    existing_ids = {h.id for h in hits}
    for c in uow.characters.search_by_name(q, limit=limit * 2):
        if c.id in existing_ids:
            continue
        score = 1.0
        if query_vec is not None and c.embedding:
            try:
                import json as _json

                emb: list[float] = _json.loads(c.embedding)
                score = _cosine(query_vec, emb)
            except Exception:  # noqa: BLE001
                score = 1.0
        else:
            if q_lower in c.canonical_name:
                score = 2.0
        hits.append(SearchHit(id=c.id, name=c.name, kind="character", score=score))

    for o in uow.organizations.search_by_name(q, limit=limit):
        score = 2.0 if q_lower in o.name.lower() else 1.0
        hits.append(SearchHit(id=o.id, name=o.name, kind="organization", score=score))

    for loc in uow.locations.search_by_name(q, limit=limit):
        score = 2.0 if q_lower in loc.name.lower() else 1.0
        hits.append(SearchHit(id=loc.id, name=loc.name, kind="location", score=score))

    hits.sort(key=lambda h: h.score, reverse=True)
    hits = hits[:limit]
    return SearchResponse(query=q, total=len(hits), hits=hits)


@router.get("/semantic", response_model=SemanticSearchResponse)
def semantic_search(
    q: str = Query(..., min_length=1, description="Free-text query"),
    limit: int = Query(20, ge=1, le=200),
    uow: UnitOfWork = Depends(get_uow),
    encoder=Depends(get_encoder),
) -> SemanticSearchResponse:
    """Semantic search across characters using vector similarity."""
    use_case = SemanticSearch(uow, encoder)
    result = use_case.search_characters(q, limit=limit)

    return SemanticSearchResponse(
        query=result.query,
        total=result.total,
        results=[
            SemanticSearchHit(
                id=r.id,
                name=r.name,
                kind=r.kind,
                score=r.score,
                canonical_name=r.canonical_name,
                description=r.description,
                metadata=r.metadata,
            )
            for r in result.results
        ],
        search_type=result.search_type,
        novel_id=result.novel_id,
    )


@router.get("/similar/{character_id}", response_model=CharacterSimilarityResponse)
def similar_characters(
    character_id: str,
    limit: int = Query(10, ge=1, le=100),
    threshold: float = Query(0.3, ge=0.0, le=1.0),
    uow: UnitOfWork = Depends(get_uow),
    encoder=Depends(get_encoder),
) -> CharacterSimilarityResponse:
    """Find characters similar to a given character using embedding vectors."""
    use_case = SemanticSearch(uow, encoder)
    result = use_case.search_similar_characters(character_id, limit=limit, threshold=threshold)

    return CharacterSimilarityResponse(
        character_id=result.character_id,
        character_name=result.character_name,
        similar_characters=[
            CharacterSimilarityHit(
                id=c.id,
                name=c.name,
                score=c.score,
                canonical_name=c.canonical_name,
            )
            for c in result.similar_characters
        ],
        similarity_threshold=result.similarity_threshold,
    )


@router.get("/cross-novel", response_model=SemanticSearchResponse)
def cross_novel_search(
    q: str = Query(..., min_length=1, description="Free-text query"),
    limit: int = Query(20, ge=1, le=200),
    uow: UnitOfWork = Depends(get_uow),
    encoder=Depends(get_encoder),
) -> SemanticSearchResponse:
    """Search across all novels using semantic similarity."""
    use_case = SemanticSearch(uow, encoder)
    result = use_case.search_cross_novel(q, limit=limit)

    return SemanticSearchResponse(
        query=result.query,
        total=result.total,
        results=[
            SemanticSearchHit(
                id=r.id,
                name=r.name,
                kind=r.kind,
                score=r.score,
                canonical_name=r.canonical_name,
                description=r.description,
                metadata=r.metadata,
            )
            for r in result.results
        ],
        search_type=result.search_type,
        novel_id=result.novel_id,
    )
