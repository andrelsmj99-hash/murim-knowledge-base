"""
Use case: knowledge graph traversal for finding paths and networks.

This use case builds on BuildKnowledgeGraphUseCase to provide:
- Shortest path finding between two characters
- Character network extraction (neighbors within N hops)
- Graph statistics and metrics
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import networkx as nx

from app.core.entities.search_result import CharacterNetworkResult, GraphPathResult
from app.core.unit_of_work import UnitOfWork
from app.core.use_cases.build_knowledge_graph import BuildKnowledgeGraphUseCase

logger = logging.getLogger(__name__)


@dataclass
class GraphTraversalConfig:
    """Configuration for graph traversal."""

    max_path_length: int = 10
    max_network_depth: int = 2
    max_network_nodes: int = 100


class KnowledgeGraphTraversal:
    """Use case for knowledge graph traversal operations."""

    def __init__(
        self,
        uow: UnitOfWork,
        config: GraphTraversalConfig | None = None,
    ) -> None:
        self.uow = uow
        self.config = config or GraphTraversalConfig()
        self._graph: nx.Graph | None = None

    def _get_graph(self, novel_id: str | None = None) -> nx.Graph:
        """Get or build the knowledge graph."""
        if self._graph is None:
            use_case = BuildKnowledgeGraphUseCase(self.uow, directed=False)
            self._graph = use_case.execute(novel_id=novel_id)
        return self._graph

    def find_path(
        self,
        source_id: str,
        target_id: str,
        *,
        novel_id: str | None = None,
    ) -> GraphPathResult:
        """
        Find the shortest path between two characters.

        Args:
            source_id: Source character ID (without "char:" prefix)
            target_id: Target character ID (without "char:" prefix)
            novel_id: Optional novel ID to restrict the graph

        Returns:
            GraphPathResult with the shortest path
        """
        graph = self._get_graph(novel_id)

        source_node = f"char:{source_id}"
        target_node = f"char:{target_id}"

        # Get node names
        source_name = graph.nodes.get(source_node, {}).get("name", source_id)
        target_name = graph.nodes.get(target_node, {}).get("name", target_id)

        try:
            path = nx.shortest_path(graph, source=source_node, target=target_node)
            path_names = [graph.nodes.get(node, {}).get("name", node) for node in path]
            return GraphPathResult(
                source_id=source_id,
                source_name=source_name,
                target_id=target_id,
                target_name=target_name,
                path=path,
                path_length=len(path) - 1,
                path_names=path_names,
            )
        except nx.NetworkXNoPath:
            return GraphPathResult(
                source_id=source_id,
                source_name=source_name,
                target_id=target_id,
                target_name=target_name,
                path=[],
                path_length=0,
                path_names=[],
            )
        except nx.NodeNotFound as e:
            logger.warning("Node not found in graph: %s", e)
            return GraphPathResult(
                source_id=source_id,
                source_name=source_name,
                target_id=target_id,
                target_name=target_name,
                path=[],
                path_length=0,
                path_names=[],
            )

    def get_character_network(
        self,
        character_id: str,
        *,
        depth: int | None = None,
        novel_id: str | None = None,
    ) -> CharacterNetworkResult:
        """
        Get the network of characters connected to a given character.

        Args:
            character_id: Character ID (without "char:" prefix)
            depth: Number of hops to traverse (default from config)
            novel_id: Optional novel ID to restrict the graph

        Returns:
            CharacterNetworkResult with nodes and edges
        """
        depth = depth or self.config.max_network_depth
        graph = self._get_graph(novel_id)

        center_node = f"char:{character_id}"
        center_name = graph.nodes.get(center_node, {}).get("name", character_id)

        if center_node not in graph:
            return CharacterNetworkResult(
                center_character_id=character_id,
                center_character_name=center_name,
                nodes=[],
                edges=[],
                depth=depth,
                node_count=0,
                edge_count=0,
            )

        # BFS to get neighbors within depth
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(center_node, 0)]
        nodes_in_network: list[str] = []

        while queue and len(nodes_in_network) < self.config.max_network_nodes:
            node, current_depth = queue.pop(0)
            if node in visited or current_depth > depth:
                continue
            visited.add(node)
            nodes_in_network.append(node)

            if current_depth < depth:
                for neighbor in graph.neighbors(node):
                    if neighbor not in visited:
                        queue.append((neighbor, current_depth + 1))

        # Extract nodes and edges
        nodes = []
        for node_id in nodes_in_network:
            node_attrs = graph.nodes.get(node_id, {})
            nodes.append(
                {
                    "id": node_id,
                    "kind": node_attrs.get("kind", "unknown"),
                    "name": node_attrs.get("name", node_id),
                    "depth": 0,  # Will be computed below
                }
            )

        # Compute depth for each node
        node_depths = {center_node: 0}
        queue = [(center_node, 0)]
        while queue:
            node, current_depth = queue.pop(0)
            if current_depth >= depth:
                continue
            for neighbor in graph.neighbors(node):
                if neighbor not in node_depths:
                    node_depths[neighbor] = current_depth + 1
                    queue.append((neighbor, current_depth + 1))

        # Update depths
        for node_info in nodes:
            node_info["depth"] = node_depths.get(node_info["id"], depth + 1)

        # Extract edges between nodes in network
        edges = []
        nodes_set = set(nodes_in_network)
        for u, v, attrs in graph.edges(data=True):
            if u in nodes_set and v in nodes_set:
                edges.append(
                    {
                        "source": u,
                        "target": v,
                        "kind": attrs.get("kind", "related"),
                        "attrs": {k: v for k, v in attrs.items() if k != "kind"},
                    }
                )

        return CharacterNetworkResult(
            center_character_id=character_id,
            center_character_name=center_name,
            nodes=nodes,
            edges=edges,
            depth=depth,
            node_count=len(nodes),
            edge_count=len(edges),
        )

    def get_graph_stats(
        self,
        novel_id: str | None = None,
    ) -> dict:
        """
        Get statistics about the knowledge graph.

        Args:
            novel_id: Optional novel ID to restrict the graph

        Returns:
            Dictionary with graph statistics
        """
        graph = self._get_graph(novel_id)

        # Count node types
        character_count = sum(1 for _, d in graph.nodes(data=True) if d.get("kind") == "character")
        organization_count = sum(
            1 for _, d in graph.nodes(data=True) if d.get("kind") == "organization"
        )
        location_count = sum(1 for _, d in graph.nodes(data=True) if d.get("kind") == "location")

        # Count edge types
        relationship_edges = sum(
            1 for _, _, d in graph.edges(data=True) if d.get("kind", "").startswith("rel_")
        )
        membership_edges = sum(
            1 for _, _, d in graph.edges(data=True) if d.get("kind") == "member_of"
        )

        return {
            "total_nodes": graph.number_of_nodes(),
            "total_edges": graph.number_of_edges(),
            "characters": character_count,
            "organizations": organization_count,
            "locations": location_count,
            "relationships": relationship_edges,
            "memberships": membership_edges,
            "density": nx.density(graph) if graph.number_of_nodes() > 0 else 0.0,
        }


__all__ = ["KnowledgeGraphTraversal", "GraphTraversalConfig"]
