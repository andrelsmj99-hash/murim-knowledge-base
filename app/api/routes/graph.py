"""
/graph route — exposes the NetworkX knowledge graph as JSON.

The build is delegated to :class:`BuildKnowledgeGraphUseCase` so the API
stays in sync with any future logic (novel-scoped graphs, filtered views).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_uow
from app.api.schemas import GraphEdge, GraphNode, GraphResponse
from app.core.unit_of_work import UnitOfWork
from app.core.use_cases import BuildKnowledgeGraphUseCase

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
