"""
Detect sect / clan / guild / … mentions in prose.

Two strategies are combined:
* **Lookup** — match the canonical and alias names registered in
  :data:`app.processing.patterns.ORG_PATTERNS`.
* **Suffix heuristic** — recognise ``"<Word>+<Suffix>"`` patterns
  (e.g. "Heavenly Sword Sect", "Tang Clan", "Plum Blossom Island").

The output is normalised via :data:`app.processing.patterns.ORG_LOOKUP` so
that aliases map to a single canonical name.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.processing.patterns import ORG_LOOKUP, ORG_SUFFIXES


@dataclass
class OrgMatch:
    """A detected organization mention."""

    surface: str
    canonical: str
    type: str  # "Sect", "Clan", …
    start: int
    end: int


# Suffixes sorted by length (longest first) so that "Island of" wins over "Island".
_SUFFIXES = sorted(ORG_SUFFIXES, key=len, reverse=True)
_SUFFIX_REGEX = re.compile(
    r"\b(?P<name>[A-Z][\w'\-]+(?:\s+[A-Z][\w'\-]+){0,3})\s+("
    + "|".join(re.escape(s) for s in _SUFFIXES)
    + r")\b"
)


def detect_organizations(text: str) -> list[OrgMatch]:
    """Find organization mentions in ``text``."""
    if not text:
        return []

    out: dict[str, OrgMatch] = {}

    # 1. Lookup known orgs (longest first to avoid partial matches)
    sorted_keys = sorted(ORG_LOOKUP.keys(), key=len, reverse=True)
    for key in sorted_keys:
        pat = ORG_LOOKUP[key]
        # Use a regex that matches the key as a whole word / phrase
        pattern = re.compile(r"\b" + re.escape(pat.name) + r"\b", re.IGNORECASE)
        for m in pattern.finditer(text):
            span = (m.start(), m.end())
            if span in out:
                continue
            out[span] = OrgMatch(
                surface=m.group(0),
                canonical=pat.name,
                type=pat.type,
                start=m.start(),
                end=m.end(),
            )

    # 2. Suffix-based heuristic
    for m in _SUFFIX_REGEX.finditer(text):
        span = (m.start(), m.end())
        if span in out:
            continue
        # If we already have a span that fully contains this one, skip
        if any(s <= m.start() and e >= m.end() for (s, e) in out):
            continue
        surface = m.group(0)
        # Use the matched surface as the canonical name (operator can
        # later merge it with a registered org via dedup).
        out[span] = OrgMatch(
            surface=surface,
            canonical=surface,
            type=m.group(2),
            start=m.start(),
            end=m.end(),
        )

    # Sort by position for downstream consumers
    return sorted(out.values(), key=lambda o: o.start)


def merge_aliases(matches: Iterable[OrgMatch]) -> dict[str, OrgMatch]:
    """Collapse matches that share the same canonical name."""
    out: dict[str, OrgMatch] = {}
    for m in matches:
        out.setdefault(m.canonical.lower(), m)
    return out


__all__ = ["OrgMatch", "detect_organizations", "merge_aliases"]
