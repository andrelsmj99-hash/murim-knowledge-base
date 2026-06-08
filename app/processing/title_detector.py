"""
Detect Murim/Wuxia titles associated with a character mention.

Examples::

    "Elder Lin Lei"      -> title="Elder",    name="Lin Lei"
    "Senior Brother Yi"  -> title="Senior Brother", name="Yi"
    "Young Master Wei"   -> title="Young Master",  name="Wei"
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.processing.patterns import TITLE_LOOKUP


@dataclass
class TitleMatch:
    title: str  # canonical title
    category: str
    # Where the title was attached — useful for surfacing context.
    context: str  # the original text fragment


# Compile a single big regex that catches "<Title> <Name>" at word boundaries
_TITLE_KEYS_BY_LENGTH = sorted(TITLE_LOOKUP.keys(), key=len, reverse=True)
_TITLE_REGEX = re.compile(
    r"\b("
    + "|".join(re.escape(t) for t in _TITLE_KEYS_BY_LENGTH)
    + r")\s+(?P<name>[A-Z][\w']+(?:\s+[A-Z][\w']+){0,2})\b",
    re.IGNORECASE,
)


def detect_titles(text: str) -> list[TitleMatch]:
    """Return all ``<Title> <Name>`` matches found in ``text``."""
    out: list[TitleMatch] = []
    for m in _TITLE_REGEX.finditer(text or ""):
        title_key = m.group(1).lower()
        pattern = TITLE_LOOKUP.get(title_key)
        if pattern is None:
            continue
        out.append(
            TitleMatch(
                title=pattern.title,
                category=pattern.category,
                context=m.group(0),
            )
        )
    return out


def split_title_from_name(name_with_title: str) -> tuple[str | None, str]:
    """Best-effort split of a string like ``"Elder Lin Lei"`` into ``("Elder", "Lin Lei")``."""
    if not name_with_title:
        return None, name_with_title
    for key in _TITLE_KEYS_BY_LENGTH:
        prefix = key + " "
        if name_with_title.lower().startswith(prefix):
            pattern = TITLE_LOOKUP.get(key)
            if pattern is not None:
                return pattern.title, name_with_title[len(prefix) :]
    return None, name_with_title


__all__ = ["TitleMatch", "detect_titles", "split_title_from_name"]
