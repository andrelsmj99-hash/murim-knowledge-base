"""
Extract character↔character relationships from prose.

Uses the pattern catalogue in :data:`app.processing.patterns.RELATIONSHIP_PHRASES`
combined with a simple "X of the Y" / "X of Y" / "Y's master X" fallback.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from app.processing.patterns import RELATIONSHIP_PHRASES, canonicalize_name


@dataclass
class RelationshipHit:
    """A potential relationship extracted from text."""

    source: str
    target: str
    relationship_type: str
    confidence: float
    context: str

    def canonical_pair(self) -> tuple[str, str]:
        return (canonicalize_name(self.source), canonicalize_name(self.target))


# Pronouns and generic words that should never be a relationship endpoint
_BAD_ENDPOINTS = {
    "he", "she", "it", "they", "him", "her", "them",
    "his", "her", "their", "its",
    "this", "that", "these", "those",
    "the", "a", "an", "is", "was", "and", "or", "but",
}


# Heuristics for "X's <rel> Y" possessives — note the corrected order:
#   "Di Shi's master is Qing Yan" → source="Di Shi", target="Qing Yan"
_POSSESSIVE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("master", re.compile(
        r"(?P<s>[A-Z][\w']+(?:\s+[A-Z][\w']+){0,2})'s\s+master\s+(?:is|was)\s+(?P<t>[A-Z][\w']+(?:\s+[A-Z][\w']+){0,2})",
        re.IGNORECASE,
    )),
    ("disciple", re.compile(
        r"(?P<s>[A-Z][\w']+(?:\s+[A-Z][\w']+){0,2})'s\s+disciple\s+(?:is|was)\s+(?P<t>[A-Z][\w']+(?:\s+[A-Z][\w']+){0,2})",
        re.IGNORECASE,
    )),
    ("senior_brother", re.compile(
        r"(?P<s>[A-Z][\w']+(?:\s+[A-Z][\w']+){0,2})'s\s+senior\s+brother\s+(?:is|was)\s+(?P<t>[A-Z][\w']+(?:\s+[A-Z][\w']+){0,2})",
        re.IGNORECASE,
    )),
    ("junior_brother", re.compile(
        r"(?P<s>[A-Z][\w']+(?:\s+[A-Z][\w']+){0,2})'s\s+junior\s+brother\s+(?:is|was)\s+(?P<t>[A-Z][\w']+(?:\s+[A-Z][\w']+){0,2})",
        re.IGNORECASE,
    )),
    ("father", re.compile(
        r"(?P<s>[A-Z][\w']+(?:\s+[A-Z][\w']+){0,2})'s\s+father\s+(?:is|was)\s+(?P<t>[A-Z][\w']+(?:\s+[A-Z][\w']+){0,2})",
        re.IGNORECASE,
    )),
    ("son", re.compile(
        r"(?P<s>[A-Z][\w']+(?:\s+[A-Z][\w']+){0,2})'s\s+son\s+(?:is|was)\s+(?P<t>[A-Z][\w']+(?:\s+[A-Z][\w']+){0,2})",
        re.IGNORECASE,
    )),
]


def extract_relationships(text: str) -> List[RelationshipHit]:
    """Return all relationship hits found in ``text``."""
    if not text:
        return []

    hits: List[RelationshipHit] = []
    for phrase in RELATIONSHIP_PHRASES:
        for m in phrase.pattern.finditer(text):
            source = _clean(m.group(phrase.groups[0]))
            target = _clean(m.group(phrase.groups[1]))
            if not _is_valid_endpoint(source) or not _is_valid_endpoint(target):
                continue
            if source.lower() == target.lower():
                continue
            hits.append(
                RelationshipHit(
                    source=source,
                    target=target,
                    relationship_type=phrase.relationship_type,
                    confidence=0.9,
                    context=m.group(0).strip(),
                )
            )

    for rel_type, pattern in _POSSESSIVE_PATTERNS:
        for m in pattern.finditer(text):
            source = _clean(m.group("s"))
            target = _clean(m.group("t"))
            if not _is_valid_endpoint(source) or not _is_valid_endpoint(target):
                continue
            if source.lower() == target.lower():
                continue
            hits.append(
                RelationshipHit(
                    source=source,
                    target=target,
                    relationship_type=rel_type,
                    confidence=0.8,
                    context=m.group(0).strip(),
                )
            )

    return hits


def _clean(value: str) -> str:
    if not value:
        return ""
    cleaned = " ".join(value.split())
    for prefix in ("the ", "a ", "an "):
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    return cleaned.strip()


def _is_valid_endpoint(value: str) -> bool:
    """Return True if ``value`` looks like a real character name (not a pronoun/article)."""
    if not value:
        return False
    if value.lower() in _BAD_ENDPOINTS:
        return False
    if len(value) < 2:
        return False
    return True


__all__ = ["RelationshipHit", "extract_relationships"]
