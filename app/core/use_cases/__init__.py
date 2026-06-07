"""
Domain use cases — orchestrations of repositories that implement a single
business intent. Each use case is stateless and receives a Unit of Work.
"""
from .build_knowledge_graph import BuildKnowledgeGraphUseCase, GraphStats
from .classify_character_archetype import ClassifyAllCharacters, ClassifyCharacterArchetype
from .deduplicate_characters import DeduplicateCharactersUseCase, DedupResult
from .extract_entities import ChapterExtraction, ExtractEntitiesUseCase
from .generate_embeddings import (
    EmbeddingResult,
    GenerateEmbeddingsResult,
    GenerateEmbeddingsUseCase,
)
from .ingest_chapter import IngestChapterUseCase, IngestResult
from .ingest_entities import IngestEntitiesResult, IngestEntitiesUseCase

__all__ = [
    "IngestChapterUseCase",
    "IngestResult",
    "ChapterExtraction",
    "ExtractEntitiesUseCase",
    "DedupResult",
    "DeduplicateCharactersUseCase",
    "BuildKnowledgeGraphUseCase",
    "GraphStats",
    "IngestEntitiesResult",
    "IngestEntitiesUseCase",
    "EmbeddingResult",
    "GenerateEmbeddingsResult",
    "GenerateEmbeddingsUseCase",
    "ClassifyCharacterArchetype",
    "ClassifyAllCharacters",
]
