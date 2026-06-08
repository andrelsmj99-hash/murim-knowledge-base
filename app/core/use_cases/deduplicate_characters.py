"""
Use case: deduplicate character candidates.

The same character can appear in many ways across chapters::

    "Lin Lei", "Lin Lei", "Lin Lei", "Lei", "the young master of the Baruch estate"

We want a single canonical character record with all variations as aliases.

Strategy:
1. Exact canonical-name match wins.
2. Otherwise, rapidfuzz-based string similarity above a threshold clusters
   candidates together. Threshold defaults to 85.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field

from app.core.entities import Character
from app.processing import canonicalize_name

logger = logging.getLogger(__name__)


@dataclass
class DedupResult:
    """Result of deduplicating a batch of candidates."""

    canonical_characters: list[Character] = field(default_factory=list)
    # Map of input canonical -> kept canonical name (for traceability)
    merge_map: dict[str, str] = field(default_factory=dict)


class DeduplicateCharactersUseCase:
    """
    Deduplicate a list of candidate characters.

    The use case is pure: it does not touch the DB. Callers can then pass
    the resulting :class:`Character` list to a repository.
    """

    def __init__(self, similarity_threshold: float = 85.0) -> None:
        self.threshold = similarity_threshold

    def execute(self, candidates: Iterable[Character]) -> DedupResult:
        candidates = list(candidates)
        clusters: list[list[Character]] = []
        representatives: list[str] = []  # canonical_name of cluster head

        for cand in candidates:
            key = (cand.canonical_name or canonicalize_name(cand.name)).strip()
            if not key:
                continue
            cand.canonical_name = key

            cluster_idx = self._find_cluster(key, representatives)
            if cluster_idx is None:
                clusters.append([cand])
                representatives.append(key)
            else:
                clusters[cluster_idx].append(cand)

        canonicals: list[Character] = []
        merge_map: dict[str, str] = {}
        for cluster in clusters:
            merged = self._merge_cluster(cluster)
            canonicals.append(merged)
            for c in cluster:
                merge_map[c.canonical_name] = merged.canonical_name

        logger.info(
            "Deduplicated %d candidates into %d canonical characters",
            len(candidates),
            len(canonicals),
        )
        return DedupResult(canonical_characters=canonicals, merge_map=merge_map)

    # ----------------------------------------------------------- internals

    def _find_cluster(self, key: str, representatives: list[str]) -> int | None:
        from rapidfuzz import fuzz

        for idx, rep in enumerate(representatives):
            if key == rep:
                return idx
            if fuzz.token_set_ratio(key, rep) >= self.threshold:
                return idx
        return None

    def _merge_cluster(self, cluster: list[Character]) -> Character:
        """Collapse a cluster of candidates into a single Character."""
        # Pick the most-mentioned candidate as the primary
        primary = max(cluster, key=lambda c: c.appearance_frequency or 0)
        merged = Character(
            id=primary.id,
            name=primary.name,
            canonical_name=primary.canonical_name,
            gender=primary.gender or _first_truthy(c.gender for c in cluster),
            description=primary.description or _first_truthy(c.description for c in cluster),
            first_appearance=primary.first_appearance
            or _first_truthy(c.first_appearance for c in cluster),
            appearance_frequency=sum(c.appearance_frequency or 0 for c in cluster),
            aliases=list(primary.aliases),
            titles=list(primary.titles),
            organizations=list(primary.organizations),
        )
        seen_aliases: set[str] = {merged.canonical_name.lower()}
        for c in cluster:
            for a in c.aliases:
                if a.value.lower() in seen_aliases:
                    continue
                seen_aliases.add(a.value.lower())
                merged.add_alias(a.alias_type, a.value)
            for t in c.titles:
                if t not in merged.titles:
                    merged.titles.append(t)
            for org_id in c.organizations:
                if org_id not in merged.organizations:
                    merged.organizations.append(org_id)
        return merged


def _first_truthy(values: Iterable[str | None]) -> str | None:
    for v in values:
        if v:
            return v
    return None


__all__ = ["DedupResult", "DeduplicateCharactersUseCase"]
