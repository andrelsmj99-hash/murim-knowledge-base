"""
Detect location mentions in prose.

Uses the curated list in :data:`app.processing.patterns.LOCATION_PATTERNS`
combined with a generic ``"<Word>+<GeoType>"`` heuristic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.processing.patterns import LOCATION_LOOKUP


@dataclass
class LocationMatch:
    surface: str
    canonical: str
    type: str
    start: int
    end: int


_GEO_TYPES: tuple[str, ...] = (
    "Mountain",
    "Mount",
    "Peak",
    "Valley",
    "Forest",
    "River",
    "Lake",
    "Sea",
    "Ocean",
    "City",
    "Town",
    "Village",
    "Capital",
    "Province",
    "Region",
    "Kingdom",
    "Empire",
    "Realm",
    "Island",
    "Plateau",
    "Desert",
    "Wasteland",
    "Marsh",
    "Bog",
    "Temple",
    "Plains",
    "Plains of",
    "Border",
    "Wastes",
)

_GEO_TYPE_REGEX = re.compile(
    r"\b(?P<name>[A-Z][\w'\-]+(?:\s+[A-Z][\w'\-]+){0,2})\s+("
    + "|".join(re.escape(g) for g in sorted(_GEO_TYPES, key=len, reverse=True))
    + r")\b"
)


def detect_locations(text: str) -> list[LocationMatch]:
    """Find location mentions in ``text``."""
    if not text:
        return []

    out: dict[tuple[int, int], LocationMatch] = {}

    # 1. Curated lookups
    sorted_keys = sorted(LOCATION_LOOKUP.keys(), key=len, reverse=True)
    for key in sorted_keys:
        pat = LOCATION_LOOKUP[key]
        pattern = re.compile(r"\b" + re.escape(pat.name) + r"\b", re.IGNORECASE)
        for m in pattern.finditer(text):
            span = (m.start(), m.end())
            if span not in out:
                out[span] = LocationMatch(
                    surface=m.group(0),
                    canonical=pat.name,
                    type=pat.type,
                    start=m.start(),
                    end=m.end(),
                )

    # 2. Suffix heuristic
    for m in _GEO_TYPE_REGEX.finditer(text):
        span = (m.start(), m.end())
        if span in out:
            continue
        if any(s <= m.start() and e >= m.end() for (s, e) in out):
            continue
        surface = m.group(0)
        out[span] = LocationMatch(
            surface=surface,
            canonical=surface,
            type=m.group(2),
            start=m.start(),
            end=m.end(),
        )

    return sorted(out.values(), key=lambda x: x.start)


__all__ = ["LocationMatch", "detect_locations"]
