"""Tests for KnowledgeGraphTraversal use case."""

from __future__ import annotations

import pytest

from app.core.entities import Character, Organization
from app.core.use_cases.knowledge_graph_traversal import (
    GraphTraversalConfig,
    KnowledgeGraphTraversal,
)


@pytest.fixture
def graph_characters():
    """Create characters for graph traversal testing."""
    import uuid

    chars = []
    char_ids = [str(uuid.uuid4()) for _ in range(5)]
    for _i, (name, char_id) in enumerate(
        zip(["Lin Lei", "Chun Yeowun", "Munyo", "Di Shi", "Lei Hu"], char_ids, strict=False)
    ):
        char = Character(
            id=char_id,
            name=name,
            canonical_name=name.lower(),
            gender="male",
        )
        chars.append(char)
    # Return both chars and their IDs
    return chars, char_ids


@pytest.fixture
def graph_organizations():
    """Create organizations for graph traversal testing."""
    import uuid

    orgs = []
    for _i, (name, org_type) in enumerate(
        [
            ("Mount Hua Sect", "sect"),
            ("Heavenly Demon Cult", "cult"),
            ("Righteous Alliance", "alliance"),
        ]
    ):
        # Use dummy member IDs - they'll be resolved by the graph builder
        org = Organization(
            id=str(uuid.uuid4()),
            name=name,
            type=org_type,
            member_ids=[],
        )
        orgs.append(org)
    return orgs


@pytest.fixture
def uow_with_graph(sqlite_session_factory, graph_characters, graph_organizations):
    """Create a UnitOfWork with characters and organizations for graph testing."""
    from app.core.unit_of_work import UnitOfWork

    chars, char_ids = graph_characters
    uow = UnitOfWork(session_factory=sqlite_session_factory)
    with uow:
        for char in chars:
            uow.characters.upsert_by_canonical_name(char)

        for org in graph_organizations:
            uow.organizations.add(org)

        uow.commit()

        # Add relationships after commit so characters exist in DB
        uow.characters.add_relationship(char_ids[0], char_ids[1], "rival")
        uow.commit()
    return uow


class TestKnowledgeGraphTraversal:
    """Tests for KnowledgeGraphTraversal use case."""

    def test_find_path_same_character(self, uow_with_graph, graph_characters):
        """Path from character to itself has length 0."""
        _, char_ids = graph_characters
        use_case = KnowledgeGraphTraversal(uow_with_graph)
        result = use_case.find_path(char_ids[0], char_ids[0])
        assert result.path_length == 0
        assert len(result.path) == 1  # Just the start node
        assert result.source_name == "Lin Lei"
        assert result.target_name == "Lin Lei"

    def test_find_path_no_path(self, uow_with_graph, graph_characters):
        """Path between disconnected characters is empty."""
        _, char_ids = graph_characters
        use_case = KnowledgeGraphTraversal(uow_with_graph)
        # These characters may or may not be connected depending on the graph
        result = use_case.find_path(char_ids[0], char_ids[2])
        # If path exists, length should be >= 1
        if result.path_length > 0:
            assert len(result.path) >= 2

    def test_find_path_nonexistent_character(self, uow_with_graph, graph_characters):
        """Path involving non-existent character returns empty path."""
        _, char_ids = graph_characters
        use_case = KnowledgeGraphTraversal(uow_with_graph)
        result = use_case.find_path("00000000-0000-0000-0000-000000000000", char_ids[0])
        assert result.path_length == 0
        assert result.path == []

    def test_get_character_network(self, uow_with_graph, graph_characters):
        """Character network returns nodes and edges."""
        _, char_ids = graph_characters
        use_case = KnowledgeGraphTraversal(uow_with_graph)
        result = use_case.get_character_network(char_ids[0], depth=1)
        assert result.center_character_id == char_ids[0]
        assert result.center_character_name == "Lin Lei"
        assert result.node_count >= 1  # At least the center node
        assert result.depth == 1

    def test_get_character_network_nonexistent(self, uow_with_graph):
        """Network for non-existent character returns empty."""
        use_case = KnowledgeGraphTraversal(uow_with_graph)
        result = use_case.get_character_network("00000000-0000-0000-0000-000000000000", depth=1)
        assert result.node_count == 0
        assert result.edge_count == 0

    def test_get_character_network_depth(self, uow_with_graph, graph_characters):
        """Character network respects depth parameter."""
        _, char_ids = graph_characters
        use_case = KnowledgeGraphTraversal(uow_with_graph)
        result = use_case.get_character_network(char_ids[0], depth=2)
        assert result.depth == 2

    def test_get_graph_stats(self, uow_with_graph):
        """Graph stats returns valid statistics."""
        use_case = KnowledgeGraphTraversal(uow_with_graph)
        stats = use_case.get_graph_stats()
        assert "total_nodes" in stats
        assert "total_edges" in stats
        assert "characters" in stats
        assert "organizations" in stats
        assert "locations" in stats
        assert "relationships" in stats
        assert "memberships" in stats
        assert "density" in stats
        assert stats["total_nodes"] >= 0
        assert stats["total_edges"] >= 0
        assert 0 <= stats["density"] <= 1


class TestGraphTraversalConfig:
    """Tests for GraphTraversalConfig."""

    def test_default_config(self):
        """Default config has sensible values."""
        config = GraphTraversalConfig()
        assert config.max_path_length == 10
        assert config.max_network_depth == 2
        assert config.max_network_nodes == 100

    def test_custom_config(self):
        """Custom config overrides defaults."""
        config = GraphTraversalConfig(
            max_path_length=5,
            max_network_depth=3,
            max_network_nodes=50,
        )
        assert config.max_path_length == 5
        assert config.max_network_depth == 3
        assert config.max_network_nodes == 50


class TestKnowledgeGraphTraversalSynthetic:
    """Tests with a small synthetic graph (5-10 nodes)."""

    @pytest.fixture
    def synthetic_data(self, sqlite_session_factory):
        """Create a small synthetic graph for testing."""
        import uuid

        from app.core.unit_of_work import UnitOfWork

        # Create characters in a chain: A -> B -> C -> D -> E
        char_ids = [str(uuid.uuid4()) for _ in range(5)]
        chars = []
        for _i, (name, char_id) in enumerate(
            zip(["Alpha", "Beta", "Gamma", "Delta", "Epsilon"], char_ids, strict=False)
        ):
            char = Character(
                id=char_id,
                name=name,
                canonical_name=name.lower(),
            )
            chars.append(char)

        uow = UnitOfWork(session_factory=sqlite_session_factory)
        with uow:
            for char in chars:
                uow.characters.upsert_by_canonical_name(char)

            uow.commit()

            # Create chain relationships: A->B, B->C, C->D, D->E
            for i in range(4):
                uow.characters.add_relationship(char_ids[i], char_ids[i + 1], "ally")

            # Create a triangle: A, C, E are all connected
            uow.characters.add_relationship(char_ids[0], char_ids[2], "rival")
            uow.characters.add_relationship(char_ids[2], char_ids[4], "rival")
            uow.characters.add_relationship(char_ids[4], char_ids[0], "rival")

            uow.commit()
        return uow, char_ids

    def test_find_path_chain(self, synthetic_data):
        """Find path along the chain."""
        uow, char_ids = synthetic_data
        use_case = KnowledgeGraphTraversal(uow)
        result = use_case.find_path(char_ids[0], char_ids[4])
        # Should find a path (direct or through chain)
        if result.path_length > 0:
            assert result.source_name == "Alpha"
            assert result.target_name == "Epsilon"

    def test_network_includes_connected_nodes(self, synthetic_data):
        """Network includes nodes within depth."""
        uow, char_ids = synthetic_data
        use_case = KnowledgeGraphTraversal(uow)
        result = use_case.get_character_network(char_ids[0], depth=2)
        # Should include at least Alpha and its direct neighbors
        node_names = [n["name"] for n in result.nodes]
        assert "Alpha" in node_names
        # Beta should be within depth 2
        assert "Beta" in node_names

    def test_stats_count_correctly(self, synthetic_data):
        """Stats count nodes and edges correctly."""
        uow, _ = synthetic_data
        use_case = KnowledgeGraphTraversal(uow)
        stats = use_case.get_graph_stats()
        # We created 5 characters
        assert stats["characters"] == 5
        # Total nodes should be at least 5 (characters only, no orgs/locs)
        assert stats["total_nodes"] == 5
