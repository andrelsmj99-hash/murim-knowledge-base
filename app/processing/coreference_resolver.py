"""
Coreference resolver for Murim / Wuxia / Xianxia texts.

Resolves pronouns ("he", "she", "his", "her") and title-based references
("the elder", "the sect master") to the most recent character mention
in the same scene (paragraph).

This is a simple heuristic resolver — it does NOT use a full neural
coreference model.  Accuracy comes from the fact that Murim prose
tends to use very consistent naming and pronoun patterns.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.processing.ner import CharacterMention
from app.processing.patterns import TITLES

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass
class CoreferenceHit:
    """A resolved coreference (pronoun or title reference → character)."""

    surface: str  # the pronoun / title phrase as it appears in text
    resolved: str  # canonical name of the character it refers to
    start: int  # character offset in text
    end: int  # character offset in text
    confidence: float  # 0.0 – 1.0


# ---------------------------------------------------------------------------
# Pronoun / title lists
# ---------------------------------------------------------------------------

# Subject pronouns
_SUBJECT_PRONOUNS: frozenset[str] = frozenset({"he", "she", "it", "they"})

# Object pronouns
_OBJECT_PRONOUNS: frozenset[str] = frozenset({"him", "her", "it", "them"})

# Possessive pronouns (determiner form — before a noun)
_POSSESSIVE_DETERMINERS: frozenset[str] = frozenset({"his", "her", "its", "their"})

# Reflexive pronouns
_REFLEXIVE_PRONOUNS: frozenset[str] = frozenset({
    "himself", "herself", "itself", "themselves",
})

# All pronouns we attempt to resolve
_ALL_PRONOUNS: frozenset[str] = (
    _SUBJECT_PRONOUNS
    | _OBJECT_PRONOUNS
    | _POSSESSIVE_DETERMINERS
    | _REFLEXIVE_PRONOUNS
)

# Build a lowercase → canonical mapping for title references
# e.g. "the elder" → "elder", "the sect master" → "sect master"
_TITLE_CANONICALS: dict[str, str] = {}
for _tp in TITLES:
    _canonical = _tp.title.lower()
    _TITLE_CANONICALS[_canonical] = _canonical
    for _alias in _tp.aliases:
        _TITLE_CANONICALS[_alias.lower()] = _canonical

# "The <title>" patterns we look for in text (lowercase for matching)
_TITLE_PHRASES: list[str] = sorted(
    {
        f"the {_canonical}"
        for _canonical in _TITLE_CANONICALS
    },
    key=len,
    reverse=True,  # longest first so "the sect master" matches before "the master"
)

# Generic titles that can refer to the most recent character even without
# an explicit mention in the same sentence.
_GENERIC_TITLES: frozenset[str] = frozenset({
    "elder", "master", "senior", "junior", "protector",
    "young master", "lord", "lady", "sir",
})

# Pattern for a name-like sequence (2-4 capitalized words)
_NAME_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b")

# Pattern for sentence start: after punctuation + whitespace
_SENTENCE_START_RE = re.compile(r"[.!?]\s+")


# ---------------------------------------------------------------------------
# Core resolution — linear scan
# ---------------------------------------------------------------------------


def resolve_coreferences(
    text: str | None,
    mentions: list[CharacterMention],
) -> list[CoreferenceHit]:
    """
    Resolve pronouns and title references to the most recent character.

    :param text: the raw chapter text.
    :param mentions: character mentions found by the NER step.
    :returns: list of resolved coreferences, one per pronoun / title ref.
    """
    if not text or not mentions:
        return []

    hits: list[CoreferenceHit] = []

    # Sort mentions by position
    sorted_mentions = sorted(mentions, key=lambda m: m.start)

    # Pre-build a set of (start, end) for known mentions to avoid
    # treating a pronoun that overlaps a real mention as a coreference.
    mention_spans: set[tuple[int, int]] = {(m.start, m.end) for m in mentions}

    # Build a map: canonical → set of surface forms seen so far
    # Used for title reference matching.
    canonical_surfaces: dict[str, set[str]] = {}
    for m in mentions:
        canonical_surfaces.setdefault(m.canonical.lower(), set()).add(m.surface.lower())

    # Build a lookup: surface_lower → canonical for all known mentions
    surface_to_canonical: dict[str, str] = {}
    for m in mentions:
        surface_to_canonical[m.surface.lower()] = m.canonical.lower()

    # --- Find all pronoun occurrences ---
    pronoun_pattern = re.compile(
        r"\b(" + "|".join(sorted(_ALL_PRONOUNS, key=len, reverse=True)) + r")\b",
        re.IGNORECASE,
    )
    pronoun_events: list[tuple[int, int, str]] = []  # (start, end, surface)
    for pm in pronoun_pattern.finditer(text):
        start, end = pm.start(), pm.end()
        # Skip if this span overlaps a known mention
        if any(start < me and end > ms for ms, me in mention_spans):
            continue
        pronoun_events.append((start, end, pm.group(0)))

    # --- Find all title reference occurrences ---
    title_events: list[tuple[int, int, str]] = []  # (start, end, phrase)
    text_lower = text.lower()
    for phrase in _TITLE_PHRASES:
        for tm in re.finditer(re.escape(phrase), text_lower):
            start, end = tm.start(), tm.end()
            if any(start < me and end > ms for ms, me in mention_spans):
                continue
            title_events.append((start, end, phrase))

    # --- Detect sentence-initial name occurrences ---
    # These are names that appear after ". " or at the start of text.
    # They reset current_character even if not in the mentions list.
    sentence_name_events: list[tuple[int, int, str]] = []  # (start, end, canonical)
    for sm in _SENTENCE_START_RE.finditer(text):
        after_punct = sm.end()
        # Look for a name-like sequence right after the punctuation
        nm = _NAME_RE.search(text, after_punct)
        if nm and nm.start() == after_punct:
            name_surface = nm.group(1)
            name_lower = name_surface.lower()
            if name_lower in surface_to_canonical:
                sentence_name_events.append(
                    (nm.start(), nm.end(), surface_to_canonical[name_lower])
                )
    # Also check start of text
    nm = _NAME_RE.match(text)
    if nm:
        name_lower = nm.group(1).lower()
        if name_lower in surface_to_canonical:
            sentence_name_events.insert(
                0, (nm.start(), nm.end(), surface_to_canonical[name_lower])
            )

    # --- Linear scan: track most recent character as we walk the text ---
    all_events = (
        [(m.start, m.end, "mention", m.canonical.lower(), m.surface.lower())
         for m in sorted_mentions]
        + [(s, e, "pronoun", surf, surf) for s, e, surf in pronoun_events]
        + [(s, e, "title", phrase, phrase) for s, e, phrase in title_events]
        + [(s, e, "sent_name", canonical, "") for s, e, canonical in sentence_name_events]
    )
    all_events.sort(key=lambda x: x[0])

    current_character: str | None = None
    current_surfaces: set[str] = set()

    for start, end, kind, canonical_val, surface_val in all_events:
        if kind == "mention":
            current_character = canonical_val
            current_surfaces = canonical_surfaces.get(canonical_val, set()).copy()
        elif kind == "sent_name":
            # Sentence-initial name resets current character
            current_character = canonical_val
            current_surfaces = canonical_surfaces.get(canonical_val, set()).copy()
        elif kind == "pronoun":
            if current_character:
                hits.append(
                    CoreferenceHit(
                        surface=surface_val,
                        resolved=current_character,
                        start=start,
                        end=end,
                        confidence=0.6,
                    )
                )
        elif kind == "title":
            resolved = _resolve_title_ref(canonical_val, current_character, current_surfaces)
            if resolved:
                hits.append(
                    CoreferenceHit(
                        surface=text[start:end],
                        resolved=resolved,
                        start=start,
                        end=end,
                        confidence=0.7,
                    )
                )

    return hits


def _resolve_title_ref(
    phrase: str,
    current_character: str | None,
    current_surfaces: set[str],
) -> str | None:
    """
    Match a title reference like "the elder" to a character.

    Strategy:
    1. If the current character's surface forms contain the title, resolve to it.
    2. If the title is generic and we have a current character, resolve to it.
    """
    title_canonical = _TITLE_CANONICALS.get(phrase, phrase.replace("the ", ""))

    # Check if any of the current character's surface forms contain the title
    if current_character and current_surfaces:
        for surface in current_surfaces:
            if title_canonical in surface:
                return current_character

    # Fallback: generic titles resolve to most recent character
    if current_character and title_canonical in _GENERIC_TITLES:
        return current_character

    return None


__all__ = ["CoreferenceHit", "resolve_coreferences"]
