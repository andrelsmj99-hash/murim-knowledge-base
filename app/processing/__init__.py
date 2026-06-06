"""
Natural Language Processing pipeline for Murim / Wuxia / Xianxia texts.

This package owns the heuristic extractors and pattern catalogues that
feed the higher-level use cases in :mod:`app.core.use_cases`.
"""
from .patterns import (
    TITLES,
    ORG_PATTERNS,
    ORG_SUFFIXES,
    LOCATION_PATTERNS,
    RELATIONSHIP_PHRASES,
    TITLE_LOOKUP,
    ORG_LOOKUP,
    LOCATION_LOOKUP,
    canonicalize_name,
)
from .ner import CharacterMention, ExtractedEntities, extract_entities
from .title_detector import TitleMatch, detect_titles, split_title_from_name
from .organization_detector import OrgMatch, detect_organizations, merge_aliases
from .location_detector import LocationMatch, detect_locations
from .relationship_extractor import RelationshipHit, extract_relationships

__all__ = [
    "TITLES",
    "ORG_PATTERNS",
    "ORG_SUFFIXES",
    "LOCATION_PATTERNS",
    "RELATIONSHIP_PHRASES",
    "TITLE_LOOKUP",
    "ORG_LOOKUP",
    "LOCATION_LOOKUP",
    "canonicalize_name",
    "CharacterMention",
    "ExtractedEntities",
    "extract_entities",
    "TitleMatch",
    "detect_titles",
    "split_title_from_name",
    "OrgMatch",
    "detect_organizations",
    "merge_aliases",
    "LocationMatch",
    "detect_locations",
    "RelationshipHit",
    "extract_relationships",
]
