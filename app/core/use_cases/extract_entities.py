"""
Use case: run all extractors over a chapter and aggregate the results.

This is a pure CPU step — it does NOT touch the database. Persistence
happens in :class:`IngestEntitiesUseCase`, which is the natural caller
of this use case.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.processing import (
    CharacterMention,
    CoreferenceHit,
    ExtractedEntities,
    LocationMatch,
    OrgMatch,
    RelationshipHit,
    TitleMatch,
    detect_locations,
    detect_organizations,
    detect_titles,
    extract_entities,
    extract_relationships,
    resolve_coreferences,
    split_title_from_name,
)
from app.processing.alias_detector import AliasHit, detect_aliases

logger = logging.getLogger(__name__)


@dataclass
class ChapterExtraction:
    """All entities found in a single chapter."""

    chapter_id: str | None = None
    character_mentions: list[CharacterMention] = field(default_factory=list)
    titles: list[TitleMatch] = field(default_factory=list)
    organizations: list[OrgMatch] = field(default_factory=list)
    locations: list[LocationMatch] = field(default_factory=list)
    relationships: list[RelationshipHit] = field(default_factory=list)
    aliases: list[AliasHit] = field(default_factory=list)
    coreferences: list[CoreferenceHit] = field(default_factory=list)

    def canonical_characters(self) -> set[str]:
        return {m.canonical for m in self.character_mentions if m.canonical}

    def canonical_organizations(self) -> set[str]:
        return {o.canonical.lower() for o in self.organizations if o.canonical}

    def canonical_locations(self) -> set[str]:
        return {loc.canonical.lower() for loc in self.locations if loc.canonical}

    def relationship_count(self) -> int:
        return len(self.relationships)


class ExtractEntitiesUseCase:
    """Run the full extraction pipeline on a chapter's text."""

    def __init__(self, spacy_model: str = "en_core_web_lg") -> None:
        self.spacy_model = spacy_model

    def execute(
        self,
        text: str,
        *,
        chapter_id: str | None = None,
    ) -> ChapterExtraction:
        """
        :param text: full chapter content.
        :param chapter_id: optional id used to annotate the result.
        """
        if not text or not text.strip():
            logger.debug("Empty text, skipping extraction")
            return ChapterExtraction(chapter_id=chapter_id)

        ner: ExtractedEntities = extract_entities(text, spacy_model=self.spacy_model)
        titles = detect_titles(text)
        orgs = detect_organizations(text)
        locs = detect_locations(text)
        rels = extract_relationships(text)
        alias_hits = detect_aliases(text)

        # Attach title data to mentions whose surface starts with a title
        merged_mentions = self._attach_titles(ner.character_mentions, titles)

        # Resolve pronouns and title references to characters
        coref_hits = resolve_coreferences(text, merged_mentions)

        result = ChapterExtraction(
            chapter_id=chapter_id,
            character_mentions=merged_mentions,
            titles=titles,
            organizations=orgs,
            locations=locs,
            relationships=rels,
            aliases=alias_hits,
            coreferences=coref_hits,
        )
        logger.info(
            "Extracted from chapter %s: %d chars, %d titles, %d orgs, %d locs, %d rels, %d aliases, %d corefs",
            chapter_id or "?",
            len(merged_mentions),
            len(titles),
            len(orgs),
            len(locs),
            len(rels),
            len(alias_hits),
            len(coref_hits),
        )
        return result

    @staticmethod
    def _attach_titles(
        mentions: list[CharacterMention],
        titles: list[TitleMatch],
    ) -> list[CharacterMention]:
        """Make sure the canonical name does not include a leading title."""
        for m in mentions:
            _, bare = split_title_from_name(m.surface)
            m.canonical = bare.lower().strip() or m.canonical
        return mentions


__all__ = ["ChapterExtraction", "ExtractEntitiesUseCase"]
