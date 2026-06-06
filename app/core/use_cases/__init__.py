"""
Domain use cases — orchestrations of repositories that implement a single
business intent. Each use case is stateless and receives a Unit of Work.
"""
from .ingest_chapter import IngestChapterUseCase, IngestResult
from .extract_entities import ChapterExtraction, ExtractEntitiesUseCase
from .deduplicate_characters import DedupResult, DeduplicateCharactersUseCase
from .build_knowledge_graph import BuildKnowledgeGraphUseCase, GraphStats
from .ingest_entities import IngestEntitiesResult, IngestEntitiesUseCase
from .generate_embeddings import EmbeddingResult, GenerateEmbeddingsResult, GenerateEmbeddingsUseCase

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
]
