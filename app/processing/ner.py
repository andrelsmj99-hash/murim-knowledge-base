"""
Named-entity recognition for Murim / Wuxia texts.

Backend strategy:
* If spaCy is installed and the configured model loads, use spaCy's ``PERSON``
  entities and merge them with our Murim-specific patterns.
* Otherwise, fall back to a regex + capitalization heuristic that still
  works reasonably well on translated English prose.

The detector is intentionally simple — accuracy comes from cross-checking
results against the pattern tables in :mod:`app.processing.patterns`.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Set

from app.processing.patterns import (
    NAME_TOKEN_PATTERN,
    canonicalize_name,
)

logger = logging.getLogger(__name__)


@dataclass
class CharacterMention:
    """A potential character mention found in the text."""

    surface: str  # the text as it appears
    canonical: str  # normalized for dedup
    start: int
    end: int

    def __hash__(self) -> int:  # allow dedup in sets
        return hash((self.surface.lower(), self.start, self.end))


@dataclass
class ExtractedEntities:
    """All candidate entities discovered in a chunk of text."""

    character_mentions: List[CharacterMention] = field(default_factory=list)
    person_entities: List[str] = field(default_factory=list)  # spaCy PERSON only

    def unique_canonicals(self) -> Set[str]:
        return {m.canonical for m in self.character_mentions}


# ---------------------------------------------------------------------------
# Backend loading
# ---------------------------------------------------------------------------


_SPACY_NLP = None
_SPACY_LOAD_ATTEMPTED = False


def _load_spacy(model_name: str) -> Optional[object]:
    """Load spaCy once; return ``None`` on any failure."""
    global _SPACY_NLP, _SPACY_LOAD_ATTEMPTED
    if _SPACY_LOAD_ATTEMPTED:
        return _SPACY_NLP
    _SPACY_LOAD_ATTEMPTED = True
    try:
        import spacy  # type: ignore

        _SPACY_NLP = spacy.load(model_name)
        logger.info("Loaded spaCy model %s for NER", model_name)
    except Exception as exc:  # noqa: BLE001
        logger.info("spaCy unavailable, using regex fallback: %s", exc)
        _SPACY_NLP = None
    return _SPACY_NLP


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_entities(
    text: str,
    *,
    spacy_model: str = "en_core_web_lg",
    min_name_tokens: int = 2,
) -> ExtractedEntities:
    """
    Extract candidate character mentions from ``text``.

    :param text: chapter content.
    :param spacy_model: spaCy model name (only loaded if installed).
    :param min_name_tokens: minimum number of capitalized tokens for a name
        candidate (the regex already enforces 2-4 tokens).
    """
    out = ExtractedEntities()
    if not text:
        return out

    nlp = _load_spacy(spacy_model)
    if nlp is not None:
        try:
            doc = nlp(text[:100_000])  # cap to avoid blowing up on huge chapters
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    out.person_entities.append(ent.text)
                    out.character_mentions.append(
                        CharacterMention(
                            surface=ent.text,
                            canonical=canonicalize_name(ent.text),
                            start=ent.start_char,
                            end=ent.end_char,
                        )
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning("spaCy processing failed, falling back to regex: %s", exc)

    # Always run the regex pass — it catches names spaCy misses and
    # provides spans that may not have been labelled PERSON.
    out.character_mentions.extend(_regex_mentions(text, min_name_tokens=min_name_tokens))

    # Deduplicate overlapping mentions (prefer longer surfaces)
    out.character_mentions = _dedup_overlapping(out.character_mentions)
    return out


# Common English words that often get capitalized after periods / in titles
# but are not character names.
_NON_NAME_WORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "but", "of", "in", "on", "at", "to",
    "for", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did",
    "this", "that", "these", "those",
    "i", "you", "he", "she", "it", "we", "they",
    "his", "her", "its", "their", "my", "your", "our",
    "chapter", "volume", "book", "part", "section", "prologue", "epilogue",
    "morning", "evening", "night", "day", "week", "month", "year",
    "today", "yesterday", "tomorrow",
    "north", "south", "east", "west",
    "estate", "house", "manor", "palace", "temple", "tower",
    "court", "city", "town", "village",
    "river", "mountain", "valley", "forest", "sea", "lake",
    "de", "von", "van", "le", "la", "el",
})


def _regex_mentions(text: str, *, min_name_tokens: int) -> Iterable[CharacterMention]:
    """Yield candidate character mentions using capitalization + patterns."""
    seen_spans: Set[tuple[int, int]] = set()
    for match in NAME_TOKEN_PATTERN.finditer(text):
        if match.start() == match.end():
            continue
        tokens = [t for t in match.group(0).split() if t]
        if len(tokens) < min_name_tokens:
            continue
        if any(t.isupper() and len(t) > 3 for t in tokens):
            continue
        # Drop names where every token is a generic English word
        if all(t.lower() in _NON_NAME_WORDS for t in tokens):
            continue
        # Reject when the first / last token is a known non-name (e.g. "The … Estate")
        if tokens[0].lower() in _NON_NAME_WORDS or tokens[-1].lower() in _NON_NAME_WORDS:
            continue
        span = (match.start(), match.end())
        if span in seen_spans:
            continue
        seen_spans.add(span)
        surface = match.group(0)
        yield CharacterMention(
            surface=surface,
            canonical=canonicalize_name(surface),
            start=match.start(),
            end=match.end(),
        )


def _dedup_overlapping(mentions: List[CharacterMention]) -> List[CharacterMention]:
    """Remove duplicate / nested mentions, keeping the longest surface."""
    if not mentions:
        return mentions
    sorted_ms = sorted(mentions, key=lambda m: (m.start, -(m.end - m.start)))
    kept: List[CharacterMention] = []
    last_end = -1
    for m in sorted_ms:
        if m.start >= last_end:
            kept.append(m)
            last_end = m.end
    return kept


__all__ = ["CharacterMention", "ExtractedEntities", "extract_entities"]
