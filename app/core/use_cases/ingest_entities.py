"""
Use case: persist the output of :class:`ExtractEntitiesUseCase` into the DB.

Responsibilities:
* Resolve character candidates against the existing catalogue (via the
  dedup use case) and upsert them.
* Upsert organizations, locations and their inter-entity edges.
* Bump each character's ``appearance_frequency`` by the number of mentions
  in this chapter.
* Link characters to organizations and locations via co-occurrence.
* Detect and persist aliases for characters.

This is the natural second half of the NLP pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.core.entities import (
    Character,
    Location,
    Organization,
)
from app.core.unit_of_work import UnitOfWork
from app.core.use_cases.deduplicate_characters import DeduplicateCharactersUseCase
from app.core.use_cases.extract_entities import ChapterExtraction
from app.processing import (
    canonicalize_name,
)

logger = logging.getLogger(__name__)


@dataclass
class IngestEntitiesResult:
    """Summary of what was written to the DB."""

    new_characters: int = 0
    updated_characters: int = 0
    new_organizations: int = 0
    new_locations: int = 0
    new_relationships: int = 0
    new_char_org_links: int = 0
    new_char_loc_links: int = 0
    new_aliases: int = 0
    character_ids: list[str] = field(default_factory=list)
    organization_ids: list[str] = field(default_factory=list)
    location_ids: list[str] = field(default_factory=list)


class IngestEntitiesUseCase:
    """Persist a :class:`ChapterExtraction` into the database."""

    def __init__(
        self,
        uow: UnitOfWork,
        *,
        dedup: DeduplicateCharactersUseCase | None = None,
    ) -> None:
        self.uow = uow
        self.dedup = dedup or DeduplicateCharactersUseCase()

    def execute(
        self, extraction: ChapterExtraction, *, novel_id: str | None = None
    ) -> IngestEntitiesResult:
        result = IngestEntitiesResult()

        char_index = self._ingest_characters(extraction, result, novel_id=novel_id)
        org_index = self._ingest_organizations(extraction, result, char_index)
        loc_index = self._ingest_locations(extraction, result, char_index, org_index)
        self._ingest_relationships(extraction, result, char_index, novel_id=novel_id)

        # Link characters to organizations and locations via co-occurrence
        self._link_char_org_cooccurrence(char_index, org_index, result)
        self._link_char_loc_cooccurrence(char_index, loc_index, result)

        # Detect and persist aliases
        self._ingest_aliases(extraction, char_index, result)

        self.uow.commit()
        logger.info("Ingested entities: %s", result)
        return result

    # ------------------------------------------------------------- chars

    def _ingest_characters(
        self,
        extraction: ChapterExtraction,
        result: IngestEntitiesResult,
        *,
        novel_id: str | None = None,
    ) -> dict[str, str]:
        # Build candidate Character objects from mentions
        freq: dict[str, int] = {}
        for m in extraction.character_mentions:
            key = m.canonical or canonicalize_name(m.surface)
            if not key:
                continue
            freq[key] = freq.get(key, 0) + 1

        candidates: list[Character] = []
        for key, count in freq.items():
            candidates.append(
                Character(
                    name=key.title(),
                    canonical_name=key,
                    novel_id=novel_id,
                    appearance_frequency=count,
                )
            )

        # Attach titles to candidates
        title_map: dict[str, list[str]] = {}
        for tm in extraction.titles:
            _, bare = _split_title_context(tm.context)
            key = bare.lower() if bare else ""
            if not key:
                continue
            title_map.setdefault(key, []).append(tm.title)
        for cand in candidates:
            for title_str in title_map.get(cand.canonical_name, []):
                if title_str not in cand.titles:
                    cand.titles.append(title_str)

        # Deduplicate within the chapter itself
        dedup = self.dedup.execute(candidates)

        # Upsert against the DB
        index: dict[str, str] = {}
        for cand in dedup.canonical_characters:
            existing = self.uow.characters.get_by_canonical_name(
                cand.canonical_name, novel_id=novel_id
            )
            if existing is not None:
                # Bump frequency
                existing.appearance_frequency = (
                    existing.appearance_frequency or 0
                ) + cand.appearance_frequency
                for title_str in cand.titles:
                    if title_str not in existing.titles:
                        existing.titles.append(title_str)
                for a in cand.aliases:
                    existing.add_alias(a.alias_type, a.value)
                self.uow.session.flush()
                index[cand.canonical_name] = existing.id
                result.updated_characters += 1
            else:
                created = self.uow.characters.upsert_by_canonical_name(cand)
                index[cand.canonical_name] = created.id
                if created.appearance_frequency == cand.appearance_frequency:
                    result.new_characters += 1
                else:
                    result.updated_characters += 1
        result.character_ids = sorted(set(index.values()))
        return index

    # ------------------------------------------------------------- orgs

    def _ingest_organizations(
        self,
        extraction: ChapterExtraction,
        result: IngestEntitiesResult,
        char_index: dict[str, str],
    ) -> dict[str, str]:
        seen: dict[str, str] = {}
        for match in extraction.organizations:
            key = match.canonical.lower()
            if not key or key in seen:
                continue
            existing = self.uow.organizations.get_by_name_type(match.canonical, match.type)
            if existing is not None:
                seen[key] = existing.id
            else:
                org = self.uow.organizations.upsert(
                    Organization(name=match.canonical, type=match.type)
                )
                seen[key] = org.id
                result.new_organizations += 1
        result.organization_ids = sorted(set(seen.values()))
        return seen

    # ------------------------------------------------------------ locs

    def _ingest_locations(
        self,
        extraction: ChapterExtraction,
        result: IngestEntitiesResult,
        char_index: dict[str, str],
        org_index: dict[str, str],
    ) -> dict[str, str]:
        seen: dict[str, str] = {}
        for match in extraction.locations:
            existing = self.uow.locations.get_by_name_type(match.canonical, match.type)
            if existing is not None:
                seen[match.canonical.lower()] = existing.id
                result.location_ids.append(existing.id)
            else:
                loc = self.uow.locations.upsert(Location(name=match.canonical, type=match.type))
                seen[match.canonical.lower()] = loc.id
                result.new_locations += 1
                result.location_ids.append(loc.id)
        return seen

    # ---------------------------------------------------------- rels

    def _ingest_relationships(
        self,
        extraction: ChapterExtraction,
        result: IngestEntitiesResult,
        char_index: dict[str, str],
        *,
        novel_id: str | None = None,
    ) -> None:
        for rel in extraction.relationships:
            src_key = canonicalize_name(rel.source)
            tgt_key = canonicalize_name(rel.target)
            src_id = char_index.get(src_key) or self._ensure_character(
                src_key, rel.source, result=result, novel_id=novel_id
            )
            tgt_id = char_index.get(tgt_key) or self._ensure_character(
                tgt_key, rel.target, result=result, novel_id=novel_id
            )
            if src_id == tgt_id:
                continue

            if self.uow.characters.add_relationship(src_id, tgt_id, rel.relationship_type):
                result.new_relationships += 1
                char = self.uow.characters.get(src_id)
                if char is not None:
                    char.relationships.setdefault(rel.relationship_type, []).append(tgt_id)

    # ---------------------------------------------------- co-occurrence

    def _link_char_org_cooccurrence(
        self,
        char_index: dict[str, str],
        org_index: dict[str, str],
        result: IngestEntitiesResult,
    ) -> None:
        """Link characters to organizations that appear in the same chapter."""
        for _char_canonical, char_id in char_index.items():
            for _org_canonical, org_id in org_index.items():
                if self.uow.characters.link_organization(char_id, org_id):
                    result.new_char_org_links += 1

    def _link_char_loc_cooccurrence(
        self,
        char_index: dict[str, str],
        loc_index: dict[str, str],
        result: IngestEntitiesResult,
    ) -> None:
        """Link characters to locations that appear in the same chapter."""
        for _char_canonical, char_id in char_index.items():
            for _loc_canonical, loc_id in loc_index.items():
                if self.uow.characters.link_location(char_id, loc_id):
                    result.new_char_loc_links += 1

    # -------------------------------------------------------- aliases

    def _ingest_aliases(
        self,
        extraction: ChapterExtraction,
        char_index: dict[str, str],
        result: IngestEntitiesResult,
    ) -> None:
        """Detect and persist aliases from the chapter text."""
        for alias_hit in extraction.aliases:
            # Try to match by canonical real name first
            char_key = canonicalize_name(alias_hit.canonical_real_name)
            char_id = char_index.get(char_key)
            if not char_id:
                # Try matching by canonical alias
                char_key = canonicalize_name(alias_hit.canonical_alias)
                char_id = char_index.get(char_key)
            if not char_id:
                continue
            if self.uow.characters.add_alias(char_id, "Alias", alias_hit.alias):
                result.new_aliases += 1

    def _ensure_character(
        self,
        canonical_key: str,
        surface: str,
        *,
        result: IngestEntitiesResult,
        novel_id: str | None = None,
    ) -> str:
        """Create a placeholder character on-the-fly when only seen in a relationship."""
        existing = self.uow.characters.get_by_canonical_name(canonical_key, novel_id=novel_id)
        if existing is not None:
            return existing.id
        created = self.uow.characters.upsert_by_canonical_name(
            Character(
                name=surface.title() if surface else canonical_key.title(),
                canonical_name=canonical_key,
                novel_id=novel_id,
            )
        )
        result.new_characters += 1
        return created.id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_title_context(context: str) -> tuple[str, str]:
    """Split ``"Elder Lin Lei"`` → ``("Elder", "Lin Lei")`` (best-effort)."""
    if not context:
        return "", ""
    parts = context.split(maxsplit=1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


__all__ = ["IngestEntitiesResult", "IngestEntitiesUseCase"]
