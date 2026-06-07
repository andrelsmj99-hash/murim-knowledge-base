"""
/search route — combined lexical + optional semantic search.

Strategy (degrades gracefully when the embedding model is unavailable):
1. Substring / case-insensitive search across characters, orgs, locations.
2. If the sentence-transformers model is loaded, score results by cosine
   similarity to the query embedding (using cached ``Character.embedding``).
3. Return the top ``limit`` hits across all kinds, sorted by score desc.
"""
from __future__ import annotations

import logging
import math

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_encoder, get_uow
from app.api.schemas import SearchHit, SearchResponse
from app.core.unit_of_work import UnitOfWork

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

    # --- characters ---------------------------------------------------------
    for c in uow.characters.search_by_name(q, limit=limit * 2):
        score = 1.0
        if query_vec is not None and getattr(c, "embedding", None):
            try:
                import json as _json
                emb = _json.loads(c.embedding)
                score = _cosine(query_vec, emb)
            except Exception:  # noqa: BLE001
                score = 1.0
        else:
            if q_lower in c.canonical_name:
                score = 2.0
        hits.append(
            SearchHit(id=c.id, name=c.name, kind="character", score=score)
        )

    # --- organizations ------------------------------------------------------
    for o in uow.organizations.search_by_name(q, limit=limit):
        score = 2.0 if q_lower in o.name.lower() else 1.0
        hits.append(SearchHit(id=o.id, name=o.name, kind="organization", score=score))

    # --- locations ----------------------------------------------------------
    for loc in uow.locations.search_by_name(q, limit=limit):
        score = 2.0 if q_lower in loc.name.lower() else 1.0
        hits.append(SearchHit(id=loc.id, name=loc.name, kind="location", score=score))

    hits.sort(key=lambda h: h.score, reverse=True)
    hits = hits[:limit]
    return SearchResponse(query=q, total=len(hits), hits=hits)
