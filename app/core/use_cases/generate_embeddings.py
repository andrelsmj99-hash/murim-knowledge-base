from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from app.core.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    character_id: str
    success: bool
    error: str | None = None


@dataclass
class GenerateEmbeddingsResult:
    results: list[EmbeddingResult] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.results if not r.success)


class GenerateEmbeddingsUseCase:
    def __init__(self, uow: UnitOfWork, encoder: Callable[[str], list[float] | None]) -> None:
        self.uow = uow
        self.encoder = encoder

    def execute(self, character_id: str) -> EmbeddingResult:
        character = self.uow.characters.get(character_id)
        if character is None:
            return EmbeddingResult(
                character_id=character_id, success=False, error="Character not found"
            )

        text = character.name
        if character.description:
            text = f"{character.name}. {character.description}"

        vector = self.encoder(text)
        if vector is None:
            return EmbeddingResult(
                character_id=character_id,
                success=False,
                error="Encoder failed to produce embedding",
            )

        blob = json.dumps(vector)
        self.uow.characters.set_embedding(character_id, blob)
        self.uow.commit()

        logger.info("Generated embedding for character %s (%s)", character_id, character.name)
        return EmbeddingResult(character_id=character_id, success=True)

    def execute_all(self, *, force: bool = False) -> GenerateEmbeddingsResult:
        all_chars = self.uow.characters.list(limit=10_000)
        results: list[EmbeddingResult] = []
        for c in all_chars:
            if not force and c.embedding is not None:
                continue
            result = self.execute(c.id)
            results.append(result)
        logger.info(
            "Generated embeddings for %d/%d characters",
            sum(1 for r in results if r.success),
            len(results),
        )
        return GenerateEmbeddingsResult(results=results)


__all__ = ["EmbeddingResult", "GenerateEmbeddingsResult", "GenerateEmbeddingsUseCase"]
