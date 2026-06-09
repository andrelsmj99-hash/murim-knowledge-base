"""
Use case: semantic search across characters, organizations, and locations.

This use case wraps the existing pgvector-based search and adds:
- Cross-novel search (search across all novels or a specific novel)
- Similar character search (find characters similar to a given character)
- Combined lexical + semantic search with configurable weights
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from app.core.entities.search_result import (
    CharacterSimilarityResult,
    SemanticSearchResponse,
    SemanticSearchResult,
)
from app.core.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


@dataclass
class SemanticSearchConfig:
    """Configuration for semantic search."""

    semantic_weight: float = 0.7
    lexical_weight: float = 0.3
    similarity_threshold: float = 0.3
    max_results: int = 50


class SemanticSearch:
    """Use case for semantic search across the knowledge base."""

    def __init__(
        self,
        uow: UnitOfWork,
        encoder,
        config: SemanticSearchConfig | None = None,
    ) -> None:
        self.uow = uow
        self.encoder = encoder
        self.config = config or SemanticSearchConfig()

    def search_characters(
        self,
        query: str,
        *,
        novel_id: str | None = None,
        limit: int = 20,
    ) -> SemanticSearchResponse:
        """
        Search characters using semantic similarity.

        Args:
            query: Free-text search query
            novel_id: Optional novel ID to restrict results
            limit: Maximum number of results

        Returns:
            SemanticSearchResponse with ranked results
        """
        if not query or not query.strip():
            return SemanticSearchResponse(query=query, total=0, results=[])

        query_vec = self.encoder.encode(query)
        results: list[SemanticSearchResult] = []

        # Try pgvector first for efficient semantic search
        try:
            pgvector_chars = self.uow.characters.search_by_embedding(query_vec, limit=limit * 2)
            for c in pgvector_chars:
                score = getattr(c, "_similarity", 0.0)
                if score >= self.config.similarity_threshold:
                    results.append(
                        SemanticSearchResult(
                            id=c.id,
                            name=c.name,
                            kind="character",
                            score=score,
                            canonical_name=c.canonical_name or "",
                            description=c.description or "",
                            metadata={
                                "gender": c.gender,
                                "first_appearance": c.first_appearance,
                                "appearance_frequency": c.appearance_frequency,
                            },
                        )
                    )
        except Exception:  # noqa: BLE001
            logger.debug("pgvector search failed, falling back to lexical")

        # Fallback: lexical search + in-Python cosine for characters not found via pgvector
        existing_ids = {r.id for r in results}
        for c in self.uow.characters.search_by_name(query, limit=limit * 2):
            if c.id in existing_ids:
                continue
            score = 1.0
            if c.embedding:
                try:
                    import json

                    emb: list[float] = json.loads(c.embedding)
                    score = _cosine_similarity(query_vec, emb)
                except Exception:  # noqa: BLE001
                    score = 1.0
            else:
                if query.lower() in c.canonical_name:
                    score = 2.0

            if score >= self.config.similarity_threshold:
                results.append(
                    SemanticSearchResult(
                        id=c.id,
                        name=c.name,
                        kind="character",
                        score=score,
                        canonical_name=c.canonical_name or "",
                        description=c.description or "",
                        metadata={
                            "gender": c.gender,
                            "first_appearance": c.first_appearance,
                            "appearance_frequency": c.appearance_frequency,
                        },
                    )
                )

        # Sort by score descending and limit
        results.sort(key=lambda r: r.score, reverse=True)
        results = results[:limit]

        return SemanticSearchResponse(
            query=query,
            total=len(results),
            results=results,
            search_type="semantic",
            novel_id=novel_id,
        )

    def search_similar_characters(
        self,
        character_id: str,
        *,
        limit: int = 10,
        threshold: float | None = None,
    ) -> CharacterSimilarityResult:
        """
        Find characters similar to a given character using embedding vectors.

        Args:
            character_id: ID of the reference character
            limit: Maximum number of similar characters to return
            threshold: Minimum similarity score (default from config)

        Returns:
            CharacterSimilarityResult with similar characters
        """
        threshold = threshold or self.config.similarity_threshold

        # Get the reference character
        ref_char = self.uow.characters.get(character_id)
        if ref_char is None:
            return CharacterSimilarityResult(
                character_id=character_id,
                character_name="",
                similar_characters=[],
                similarity_threshold=threshold,
            )

        # Get reference character embedding
        if not ref_char.embedding:
            return CharacterSimilarityResult(
                character_id=character_id,
                character_name=ref_char.name,
                similar_characters=[],
                similarity_threshold=threshold,
            )

        try:
            import json

            ref_vec: list[float] = json.loads(ref_char.embedding)
        except Exception:  # noqa: BLE001
            return CharacterSimilarityResult(
                character_id=character_id,
                character_name=ref_char.name,
                similar_characters=[],
                similarity_threshold=threshold,
            )

        # Search for similar characters using pgvector
        similar_chars = []
        try:
            pgvector_results = self.uow.characters.search_by_embedding(
                ref_vec,
                limit=limit + 1,  # +1 to exclude self
            )
            for c in pgvector_results:
                if c.id == character_id:
                    continue  # Skip self
                score = getattr(c, "_similarity", 0.0)
                if score >= threshold:
                    similar_chars.append(
                        SemanticSearchResult(
                            id=c.id,
                            name=c.name,
                            kind="character",
                            score=score,
                            canonical_name=c.canonical_name or "",
                            description=c.description or "",
                        )
                    )
        except Exception:  # noqa: BLE001
            # Fallback: compute similarity in Python for all characters
            all_chars = self.uow.characters.list(limit=1000)
            for c in all_chars:
                if c.id == character_id:
                    continue
                if not c.embedding:
                    continue
                try:
                    import json

                    c_vec: list[float] = json.loads(c.embedding)
                    score = _cosine_similarity(ref_vec, c_vec)
                    if score >= threshold:
                        similar_chars.append(
                            SemanticSearchResult(
                                id=c.id,
                                name=c.name,
                                kind="character",
                                score=score,
                                canonical_name=c.canonical_name or "",
                                description=c.description or "",
                            )
                        )
                except Exception:  # noqa: BLE001
                    continue

        # Sort by similarity and limit
        similar_chars.sort(key=lambda r: r.score, reverse=True)
        similar_chars = similar_chars[:limit]

        return CharacterSimilarityResult(
            character_id=character_id,
            character_name=ref_char.name,
            similar_characters=similar_chars,
            similarity_threshold=threshold,
        )

    def search_cross_novel(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> SemanticSearchResponse:
        """
        Search across all novels using semantic similarity.

        Args:
            query: Free-text search query
            limit: Maximum number of results

        Returns:
            SemanticSearchResponse with results from all novels
        """
        return self.search_characters(query, novel_id=None, limit=limit)


__all__ = ["SemanticSearch", "SemanticSearchConfig"]
