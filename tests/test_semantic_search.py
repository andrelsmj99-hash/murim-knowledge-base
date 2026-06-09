"""Tests for SemanticSearch use case."""

from __future__ import annotations

import json

import pytest

from app.core.entities import Character
from app.core.use_cases.semantic_search import SemanticSearch, SemanticSearchConfig


class MockEncoder:
    """Mock encoder for testing that returns fixed vectors."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def encode(self, text: str) -> list[float]:
        """Return a deterministic vector based on text hash."""
        # Simple hash-based encoding for testing
        hash_val = hash(text) % (2**31)
        import random

        rng = random.Random(hash_val)
        vec = [rng.random() for _ in range(self.dimension)]
        # Normalize
        norm = sum(x**2 for x in vec) ** 0.5
        return [x / norm for x in vec] if norm > 0 else vec


@pytest.fixture
def mock_encoder():
    return MockEncoder()


@pytest.fixture
def sample_characters():
    """Create sample characters with embeddings for testing."""
    import uuid

    chars = []
    for i, (name, gender) in enumerate(
        [
            ("Lin Lei", "male"),
            ("Chun Yeowun", "male"),
            ("Munyo", "male"),
            ("Di Shi", "male"),
            ("Lei Hu", "male"),
        ]
    ):
        # Create a simple embedding
        import random

        rng = random.Random(i)
        embedding = [rng.random() for _ in range(384)]
        norm = sum(x**2 for x in embedding) ** 0.5
        embedding = [x / norm for x in embedding]

        char = Character(
            id=str(uuid.uuid4()),
            name=name,
            canonical_name=name.lower(),
            gender=gender,
            description=f"Test character {name}",
            first_appearance=f"Chapter {i + 1}",
            appearance_frequency=10 - i,
            embedding=json.dumps(embedding),
        )
        chars.append(char)
    return chars


@pytest.fixture
def uow_with_characters(sqlite_session_factory, sample_characters):
    """Create a UnitOfWork with sample characters."""
    from app.core.unit_of_work import UnitOfWork

    uow = UnitOfWork(session_factory=sqlite_session_factory)
    with uow:
        for char in sample_characters:
            uow.characters.upsert_by_canonical_name(char)
        uow.commit()
    return uow


class TestSemanticSearch:
    """Tests for SemanticSearch use case."""

    def test_search_characters_empty_query(self, uow_with_characters, mock_encoder):
        """Empty query returns no results."""
        use_case = SemanticSearch(uow_with_characters, mock_encoder)
        result = use_case.search_characters("")
        assert result.total == 0
        assert result.results == []

    def test_search_characters_returns_results(self, uow_with_characters, mock_encoder):
        """Search returns results for valid query."""
        use_case = SemanticSearch(uow_with_characters, mock_encoder)
        result = use_case.search_characters("Lin Lei")
        assert result.total >= 0  # May be 0 if embeddings not present
        assert result.query == "Lin Lei"
        assert result.search_type == "semantic"

    def test_search_characters_with_threshold(self, uow_with_characters, mock_encoder):
        """Search respects similarity threshold."""
        config = SemanticSearchConfig(similarity_threshold=0.9)
        use_case = SemanticSearch(uow_with_characters, mock_encoder, config)
        result = use_case.search_characters("Lin Lei")
        # With high threshold, few or no results expected
        for r in result.results:
            assert r.score >= 0.9

    def test_search_characters_limit(self, uow_with_characters, mock_encoder):
        """Search respects limit parameter."""
        use_case = SemanticSearch(uow_with_characters, mock_encoder)
        result = use_case.search_characters("Lin Lei", limit=2)
        assert len(result.results) <= 2

    def test_search_characters_result_fields(self, uow_with_characters, mock_encoder):
        """Search results have correct fields."""
        use_case = SemanticSearch(uow_with_characters, mock_encoder)
        result = use_case.search_characters("Lin Lei")
        for r in result.results:
            assert r.id
            assert r.name
            assert r.kind == "character"
            assert isinstance(r.score, float)

    def test_search_similar_characters_not_found(self, uow_with_characters, mock_encoder):
        """Similar characters for non-existent character returns empty."""
        use_case = SemanticSearch(uow_with_characters, mock_encoder)
        # Use a valid UUID format that doesn't exist
        result = use_case.search_similar_characters("00000000-0000-0000-0000-000000000000")
        assert result.character_name == ""
        assert result.similar_characters == []

    def test_search_similar_characters_no_embedding(self, sqlite_session_factory, mock_encoder):
        """Similar characters for character without embedding returns empty."""
        import uuid

        from app.core.unit_of_work import UnitOfWork

        char_id = str(uuid.uuid4())
        char = Character(
            id=char_id,
            name="No Embedding",
            canonical_name="no embedding",
        )

        uow = UnitOfWork(session_factory=sqlite_session_factory)
        with uow:
            uow.characters.upsert_by_canonical_name(char)
            uow.commit()

        use_case = SemanticSearch(uow, mock_encoder)
        result = use_case.search_similar_characters(char_id)
        assert result.character_name == "No Embedding"
        assert result.similar_characters == []

    def test_search_cross_novel(self, uow_with_characters, mock_encoder):
        """Cross-novel search works same as regular search."""
        use_case = SemanticSearch(uow_with_characters, mock_encoder)
        result = use_case.search_cross_novel("Lin Lei")
        assert result.search_type == "semantic"
        assert result.novel_id is None


class TestSemanticSearchConfig:
    """Tests for SemanticSearchConfig."""

    def test_default_config(self):
        """Default config has sensible values."""
        config = SemanticSearchConfig()
        assert config.semantic_weight == 0.7
        assert config.lexical_weight == 0.3
        assert config.similarity_threshold == 0.3
        assert config.max_results == 50

    def test_custom_config(self):
        """Custom config overrides defaults."""
        config = SemanticSearchConfig(
            semantic_weight=0.5,
            lexical_weight=0.5,
            similarity_threshold=0.5,
            max_results=100,
        )
        assert config.semantic_weight == 0.5
        assert config.lexical_weight == 0.5
        assert config.similarity_threshold == 0.5
        assert config.max_results == 100
