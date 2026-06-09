"""
/graph route — exposes the NetworkX knowledge graph as JSON.

The build is delegated to :class:`BuildKnowledgeGraphUseCase` so the API
stays in sync with any future logic (novel-scoped graphs, filtered views).

Provides endpoints for:
- GET /graph: Get the full knowledge graph
- GET /graph/character/{character_id}: Get character network
- GET /graph/path: Find shortest path between characters
- GET /graph/stats: Get graph statistics
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_uow
from app.api.schemas import (
    CharacterNetworkResponse,
    GraphEdge,
    GraphNetworkEdge,
    GraphNetworkNode,
    GraphNode,
    GraphPathResponse,
    GraphResponse,
    GraphStatsResponse,
)
from app.core.unit_of_work import UnitOfWork
from app.core.use_cases import BuildKnowledgeGraphUseCase
from app.core.use_cases.knowledge_graph_traversal import KnowledgeGraphTraversal

router = APIRouter()


@router.get("", response_model=GraphResponse)
def get_graph(
    novel_id: str | None = Query(None, description="Restrict the graph to one novel"),
    uow: UnitOfWork = Depends(get_uow),
) -> GraphResponse:
    use_case = BuildKnowledgeGraphUseCase(uow)
    graph = use_case.execute(novel_id=novel_id)

    nodes = [
        GraphNode(
            id=node,
            kind=attrs.get("kind", "unknown"),
            label=attrs.get("name") or attrs.get("title") or node,
            attrs={k: v for k, v in attrs.items() if v is not None},
        )
        for node, attrs in graph.nodes(data=True)
    ]
    edges = [
        GraphEdge(
            source=u,
            target=v,
            kind=attrs.get("kind", "related"),
            attrs={k: v for k, v in attrs.items() if k != "kind" and v is not None},
        )
        for u, v, attrs in graph.edges(data=True)
    ]
    stats = {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "characters": sum(1 for _, d in graph.nodes(data=True) if d.get("kind") == "character"),
        "organizations": sum(
            1 for _, d in graph.nodes(data=True) if d.get("kind") == "organization"
        ),
        "locations": sum(1 for _, d in graph.nodes(data=True) if d.get("kind") == "location"),
    }
    return GraphResponse(nodes=nodes, edges=edges, stats=stats)


@router.get("/character/{character_id}", response_model=CharacterNetworkResponse)
def character_network(
    character_id: str,
    depth: int = Query(2, ge=1, le=5, description="Number of hops to traverse"),
    uow: UnitOfWork = Depends(get_uow),
) -> CharacterNetworkResponse:
    """Get the network of characters connected to a given character."""
    use_case = KnowledgeGraphTraversal(uow)
    result = use_case.get_character_network(character_id, depth=depth)

    return CharacterNetworkResponse(
        center_character_id=result.center_character_id,
        center_character_name=result.center_character_name,
        nodes=[
            GraphNetworkNode(
                id=n["id"],
                kind=n["kind"],
                name=n["name"],
                depth=n["depth"],
            )
            for n in result.nodes
        ],
        edges=[
            GraphNetworkEdge(
                source=e["source"],
                target=e["target"],
                kind=e["kind"],
                attrs=e.get("attrs", {}),
            )
            for e in result.edges
        ],
        depth=result.depth,
        node_count=result.node_count,
        edge_count=result.edge_count,
    )


@router.get("/path", response_model=GraphPathResponse)
def find_path(
    source_id: str = Query(..., description="Source character ID"),
    target_id: str = Query(..., description="Target character ID"),
    uow: UnitOfWork = Depends(get_uow),
) -> GraphPathResponse:
    """Find the shortest path between two characters."""
    use_case = KnowledgeGraphTraversal(uow)
    result = use_case.find_path(source_id, target_id)

    return GraphPathResponse(
        source_id=result.source_id,
        source_name=result.source_name,
        target_id=result.target_id,
        target_name=result.target_name,
        path=result.path,
        path_length=result.path_length,
        path_names=result.path_names,
    )


@router.get("/stats", response_model=GraphStatsResponse)
def graph_stats(
    uow: UnitOfWork = Depends(get_uow),
) -> GraphStatsResponse:
    """Get statistics about the knowledge graph."""
    use_case = KnowledgeGraphTraversal(uow)
    stats = use_case.get_graph_stats()

    return GraphStatsResponse(
        total_nodes=stats["total_nodes"],
        total_edges=stats["total_edges"],
        characters=stats["characters"],
        organizations=stats["organizations"],
        locations=stats["locations"],
        relationships=stats["relationships"],
        memberships=stats["memberships"],
        density=stats["density"],
    )
