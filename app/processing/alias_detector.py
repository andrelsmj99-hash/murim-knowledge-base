"""
Detect character aliases from context phrases in prose.

Recognises patterns like:
* "X, also known as <alias>"
* "X, whose real name was <name>"
* "X, formerly known as <alias>"
* "X, once called <alias>"
* "born as <name>"
* "known as <alias>"
* "called <alias>"
* "named <alias>"
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.processing.patterns import canonicalize_name


@dataclass
class AliasHit:
    """An alias relationship detected from context."""

    real_name: str  # the "true" name (may be empty if only alias found)
    alias: str  # the alias / epithet / title
    canonical_real_name: str  # normalized real_name
    canonical_alias: str  # normalized alias
    confidence: float  # 0.0–1.0
    context: str  # the matched text fragment


# ---------------------------------------------------------------------------
# Name pattern — 1–3 capitalized words
# ---------------------------------------------------------------------------
_NAME = r"[A-Z][\w']+(?:\s+[A-Z][\w']+){0,2}"

# Trailing boundary — comma, period, semicolon, or sentence-level connector
_BOUNDARY = r"(?:[.,;:!\?]|(?:\s+(?:and|but|who|before|after|while|that|whose))|\s*$)"

# ---------------------------------------------------------------------------
# Pattern catalogue: (compiled_regex, name_group, alias_group, confidence)
# ---------------------------------------------------------------------------
_ALIAS_PATTERNS: list[tuple[re.Pattern[str], str, str, float]] = [
    # ── "X, also known as <alias>" ──────────────────────────────────────
    (
        re.compile(
            rf"(?P<name>{_NAME})"
            r",?\s+also\s+known\s+as\s+"
            rf"(?P<alias>{_NAME}(?:\s+of\s+{_NAME})?)" + _BOUNDARY,
            re.IGNORECASE,
        ),
        "name",
        "alias",
        0.85,
    ),
    # ── "X, also called <alias>" ────────────────────────────────────────
    (
        re.compile(
            rf"(?P<name>{_NAME})"
            r",?\s+also\s+called\s+"
            rf"(?P<alias>{_NAME})" + _BOUNDARY,
            re.IGNORECASE,
        ),
        "name",
        "alias",
        0.85,
    ),
    # ── "X, whose real name was <name>" ─────────────────────────────────
    (
        re.compile(
            rf"(?P<alias>{_NAME})"
            r",?\s+whose\s+real\s+name\s+(?:is|was)\s+"
            rf"(?P<name>{_NAME})",
            re.IGNORECASE,
        ),
        "name",
        "alias",
        0.95,
    ),
    # ── "X, whose true name was <name>" ─────────────────────────────────
    (
        re.compile(
            rf"(?P<alias>{_NAME})"
            r",?\s+whose\s+true\s+name\s+(?:is|was)\s+"
            rf"(?P<name>{_NAME})",
            re.IGNORECASE,
        ),
        "name",
        "alias",
        0.95,
    ),
    # ── "X, whose name was <name>" ──────────────────────────────────────
    (
        re.compile(
            rf"(?P<alias>{_NAME})"
            r",?\s+whose\s+name\s+(?:is|was)\s+"
            rf"(?P<name>{_NAME})",
            re.IGNORECASE,
        ),
        "name",
        "alias",
        0.90,
    ),
    # ── "X, formerly known as <alias>" ──────────────────────────────────
    (
        re.compile(
            rf"(?P<name>{_NAME})"
            r",?\s+formerly\s+known\s+as\s+"
            rf"(?P<alias>{_NAME})" + _BOUNDARY,
            re.IGNORECASE,
        ),
        "name",
        "alias",
        0.85,
    ),
    # ── "X, once called <alias>" ────────────────────────────────────────
    (
        re.compile(
            rf"(?P<name>{_NAME})"
            r",?\s+once\s+called\s+"
            rf"(?P<alias>{_NAME})" + _BOUNDARY,
            re.IGNORECASE,
        ),
        "name",
        "alias",
        0.80,
    ),
    # ── "born as <name>" (name is the birth name; look for alias after) ─
    (
        re.compile(
            r"[Bb]orn\s+as\s+"
            rf"(?P<name>{_NAME})"
            r"(?:[.,;!\?]|\s+and|\s+but|\s+who|\s+before|\s+after|\s*,|\s*$)",
            re.IGNORECASE,
        ),
        "name",
        "_follow_alias",
        0.85,
    ),
    # ── "X, known as <alias>" ───────────────────────────────────────────
    (
        re.compile(
            rf"(?P<name>{_NAME})"
            r",?\s+known\s+as\s+"
            rf"(?P<alias>{_NAME})" + _BOUNDARY,
            re.IGNORECASE,
        ),
        "name",
        "alias",
        0.75,
    ),
    # ── "X called <alias>" (no comma — lower confidence) ────────────────
    (
        re.compile(
            rf"(?P<name>{_NAME})"
            r"\s+called\s+"
            rf"(?P<alias>{_NAME})" + _BOUNDARY,
            re.IGNORECASE,
        ),
        "name",
        "alias",
        0.70,
    ),
    # ── "X named <alias>" ───────────────────────────────────────────────
    (
        re.compile(
            rf"(?P<name>{_NAME})"
            r"\s+named\s+"
            rf"(?P<alias>{_NAME})" + _BOUNDARY,
            re.IGNORECASE,
        ),
        "name",
        "alias",
        0.70,
    ),
]


def detect_aliases(text: str) -> list[AliasHit]:
    """
    Detect alias relationships from context phrases in ``text``.

    Returns a list of :class:`AliasHit` objects, one per detected alias.
    """
    if not text:
        return []

    hits: list[AliasHit] = []
    seen: set[tuple[str, str]] = set()

    for pattern, _name_group, alias_group, confidence in _ALIAS_PATTERNS:
        for m in pattern.finditer(text):
            # Resolve the real name
            real_name = _clean_name(m.group("name")) if "name" in m.groupdict() else ""

            # Resolve the alias
            if alias_group == "_follow_alias":
                # "born as X" → look for what they became later in the sentence
                alias_text = _find_following_alias(text, m.end())
            else:
                alias_text = _clean_name(m.group("alias")) if "alias" in m.groupdict() else ""

            # Skip if both are empty or identical
            if not real_name and not alias_text:
                continue
            if real_name and alias_text and real_name.lower() == alias_text.lower():
                continue

            # Deduplicate
            key = (real_name.lower(), alias_text.lower())
            if key in seen:
                continue
            seen.add(key)

            # Build context fragment (generous window)
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            context = text[start:end].strip()

            hits.append(
                AliasHit(
                    real_name=real_name,
                    alias=alias_text,
                    canonical_real_name=canonicalize_name(real_name) if real_name else "",
                    canonical_alias=canonicalize_name(alias_text) if alias_text else "",
                    confidence=confidence,
                    context=context,
                )
            )

    return hits


def _find_following_alias(text: str, start: int) -> str:
    """After 'born as <Name>, look for what the character became later."""
    following = text[start:]
    match = re.search(
        rf"(?:became|known|called|named|reborn)\s+(?:as\s+)?"
        rf"(?P<a>{_NAME})",
        following,
        re.IGNORECASE,
    )
    if match:
        return _clean_name(match.group("a"))
    return ""


def _clean_name(value: str) -> str:
    """Strip trailing punctuation and extra whitespace from a name."""
    if not value:
        return ""
    cleaned = value.strip()
    # Remove trailing punctuation
    while cleaned and cleaned[-1] in ".,;:!?)\"'":
        cleaned = cleaned[:-1]
    return " ".join(cleaned.split()).strip()


__all__ = ["AliasHit", "detect_aliases"]
