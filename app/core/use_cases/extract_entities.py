"""
Use case: run all extractors over a chapter and aggregate the results.

This is a pure CPU step — it does NOT touch the database. Persistence
happens in :class:`IngestEntitiesUseCase`, which is the natural caller
of this use case.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from app.processing import (
    CharacterMention,
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
    split_title_from_name,
)

logger = logging.getLogger(__name__)


@dataclass
class ChapterExtraction:
    """All entities found in a single chapter."""

    chapter_id: Optional[str] = None
    character_mentions: List[CharacterMention] = field(default_factory=list)
    titles: List[TitleMatch] = field(default_factory=list)
    organizations: List[OrgMatch] = field(default_factory=list)
    locations: List[LocationMatch] = field(default_factory=list)
    relationships: List[RelationshipHit] = field(default_factory=list)

    def canonical_characters(self) -> set[str]:
        return {m.canonical for m in self.character_mentions if m.canonical}

    def canonical_organizations(self) -> set[str]:
        return {o.canonical.lower() for o in self.organizations if o.canonical}

    def canonical_locations(self) -> set[str]:
        return {l.canonical.lower() for l in self.locations if l.canonical}

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
        chapter_id: Optional[str] = None,
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

        # Attach title data to mentions whose surface starts with a title
        merged_mentions = self._attach_titles(ner.character_mentions, titles)

        result = ChapterExtraction(
            chapter_id=chapter_id,
            character_mentions=merged_mentions,
            titles=titles,
            organizations=orgs,
            locations=locs,
            relationships=rels,
        )
        logger.info(
            "Extracted from chapter %s: %d chars, %d titles, %d orgs, %d locs, %d rels",
            chapter_id or "?",
            len(merged_mentions),
            len(titles),
            len(orgs),
            len(locs),
            len(rels),
        )
        return result

    @staticmethod
    def _attach_titles(
        mentions: List[CharacterMention],
        titles: List[TitleMatch],
    ) -> List[CharacterMention]:
        """Make sure the canonical name does not include a leading title."""
        for m in mentions:
            _, bare = split_title_from_name(m.surface)
            m.canonical = bare.lower().strip() or m.canonical
        return mentions


__all__ = ["ChapterExtraction", "ExtractEntitiesUseCase"]
