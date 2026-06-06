"""
Use case: build a NetworkX knowledge graph from the persisted data.

Output graphs use the following schema::

    Character node      attrs: kind="character", name, gender, frequency
    Organization node   attrs: kind="organization", name, type
    Location node       attrs: kind="location", name, type
    Novel node          attrs: kind="novel", title, author

    Edges:
        (:Character)-[:MEMBER_OF {role?}]->(:Organization)
        (:Character)-[:LOCATED_IN]->(:Location)
        (:Character)-[:REL_{TYPE}]->(:Character)
        (:Organization)-[:RIVAL]->(:Organization)
        (:Organization)-[:ALLY]->(:Organization)
        (:Novel)-[:HAS_CHARACTER]->(:Character)
        (:Organization)-[:HQ_IN]->(:Location)

The graph is the contract the dashboard / API use to power visualizations.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import networkx as nx

from app.core.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


@dataclass
class GraphStats:
    characters: int
    organizations: int
    locations: int
    relationships: int


class BuildKnowledgeGraphUseCase:
    """Build a :class:`networkx.Graph` from the persisted entities."""

    def __init__(self, uow: UnitOfWork, *, directed: bool = True) -> None:
        self.uow = uow
        self.directed = directed

    def execute(self, novel_id: Optional[str] = None) -> nx.Graph:
        """Build the graph. When ``novel_id`` is given, restrict characters to that novel."""
        G = nx.DiGraph() if self.directed else nx.Graph()

        # --- characters --------------------------------------------------
        characters = self.uow.characters.list(limit=10_000)
        for c in characters:
            G.add_node(
                f"char:{c.id}",
                kind="character",
                name=c.name,
                canonical_name=c.canonical_name,
                gender=c.gender,
                frequency=c.appearance_frequency,
            )

        # --- organizations -----------------------------------------------
        orgs = self.uow.organizations.list(limit=10_000)
        org_index = {str(o.id): o for o in orgs}
        for o in orgs:
            G.add_node(
                f"org:{o.id}",
                kind="organization",
                name=o.name,
                type=o.type,
            )
            for member_id in o.member_ids:
                G.add_edge(f"char:{member_id}", f"org:{o.id}", kind="member_of")
            if o.headquarters_id:
                G.add_edge(
                    f"org:{o.id}",
                    f"loc:{o.headquarters_id}",
                    kind="hq_in",
                )

        # --- organization relationships ---------------------------------
        for o in orgs:
            for rel_type, target_ids in o.relationships.items():
                edge_kind = rel_type  # "rival", "ally", …
                for tid in target_ids:
                    G.add_edge(
                        f"org:{o.id}",
                        f"org:{tid}",
                        kind=edge_kind,
                    )

        # --- locations ---------------------------------------------------
        locations = self.uow.locations.list(limit=10_000)
        for l in locations:
            G.add_node(
                f"loc:{l.id}",
                kind="location",
                name=l.name,
                type=l.type,
            )
            if l.parent_location_id:
                G.add_edge(
                    f"loc:{l.id}",
                    f"loc:{l.parent_location_id}",
                    kind="sub_location_of",
                )

        # --- character relationships ------------------------------------
        seen_rels: set[tuple[str, str, str]] = set()
        for c in characters:
            for rel_type, target_ids in c.relationships.items():
                for tid in target_ids:
                    key = (c.id, tid, rel_type)
                    if key in seen_rels:
                        continue
                    seen_rels.add(key)
                    G.add_edge(
                        f"char:{c.id}",
                        f"char:{tid}",
                        kind=f"rel_{rel_type}",
                        relationship_type=rel_type,
                    )

        # --- novel hub ---------------------------------------------------
        novel_node_added = False
        if novel_id is not None:
            novel = self.uow.novels.get(novel_id)
            if novel is not None:
                G.add_node(
                    f"novel:{novel.id}",
                    kind="novel",
                    title=novel.title,
                    author=novel.author,
                )
                novel_node_added = True
                for c in characters:
                    G.add_edge(f"novel:{novel.id}", f"char:{c.id}", kind="has_character")

        stats = GraphStats(
            characters=len(characters),
            organizations=len(orgs),
            locations=len(locations),
            relationships=sum(1 for _, _, d in G.edges(data=True) if d.get("kind", "").startswith(("rel_", "rival", "ally"))),
        )
        logger.info(
            "Built knowledge graph: %d nodes, %d edges (stats=%s)",
            G.number_of_nodes(),
            G.number_of_edges(),
            stats,
        )
        return G


__all__ = ["BuildKnowledgeGraphUseCase", "GraphStats"]
