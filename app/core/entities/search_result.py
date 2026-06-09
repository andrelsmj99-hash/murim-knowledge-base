"""
Domain entities for search results.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SemanticSearchResult:
    """A single search result from semantic search."""

    id: str
    name: str
    kind: str  # "character", "organization", "location"
    score: float  # Cosine similarity score (0-1)
    canonical_name: str = ""
    description: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.canonical_name = self.canonical_name or self.name.lower().strip()


@dataclass
class SemanticSearchResponse:
    """Response from semantic search with metadata."""

    query: str
    total: int
    results: list[SemanticSearchResult] = field(default_factory=list)
    search_type: str = "semantic"  # "semantic", "similar_characters", "cross_novel"
    novel_id: str | None = None


@dataclass
class CharacterSimilarityResult:
    """Result for similar character search."""

    character_id: str
    character_name: str
    similar_characters: list[SemanticSearchResult] = field(default_factory=list)
    similarity_threshold: float = 0.5


@dataclass
class GraphPathResult:
    """Result for graph traversal path finding."""

    source_id: str
    source_name: str
    target_id: str
    target_name: str
    path: list[str] = field(default_factory=list)  # List of node IDs
    path_length: int = 0
    path_names: list[str] = field(default_factory=list)  # List of node names


@dataclass
class CharacterNetworkResult:
    """Result for character network extraction."""

    center_character_id: str
    center_character_name: str
    nodes: list[dict] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)
    depth: int = 1
    node_count: int = 0
    edge_count: int = 0


__all__ = [
    "SemanticSearchResult",
    "SemanticSearchResponse",
    "CharacterSimilarityResult",
    "GraphPathResult",
    "CharacterNetworkResult",
]
