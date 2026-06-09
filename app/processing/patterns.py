"""
Murim / Wuxia / Xianxia linguistic patterns.

The Murim (武林) genre has a remarkably stable vocabulary across thousands of
web-novels. By encoding the genre's titles, sects, honorifics and
relationship phrases as data — not as hard-coded rules scattered through
the code — we can:

* Add new patterns without touching the rest of the pipeline.
* Inspect / export the pattern set for debugging and tuning.
* Reuse the same patterns across the NER, title, organization and
  relationship extractors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern

# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TitlePattern:
    """A Murim honorific / title (e.g. ``Senior``, ``Elder``)."""

    title: str
    category: str  # "rank", "respect", "family", "cultivation"
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class OrgPattern:
    """A sect / clan / guild keyword used to detect organizations in prose."""

    name: str
    type: str  # "Sect", "Clan", "Guild", "Alliance", "Cult", "Pavilion", "Palace"
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class LocationPattern:
    """A generic location type keyword (e.g. ``Mountain``, ``City``)."""

    name: str
    type: str  # "City", "Mountain", "Sect Grounds", "Valley", "Forest", "Kingdom", "River"
    aliases: tuple[str, ...] = ()


@dataclass
class RelationshipPhrase:
    """A phrase expressing a relationship between two characters."""

    relationship_type: str
    pattern: Pattern[str]
    groups: tuple[int, int]  # which capture groups hold (source_name, target_name)


# ---------------------------------------------------------------------------
# Titles (Murim honorifics)
# ---------------------------------------------------------------------------

TITLES: list[TitlePattern] = [
    # Cultivation ranks
    TitlePattern("Mortal", "rank", ("common mortal",)),
    TitlePattern("Martial Artist", "rank", ("martial artist",)),
    TitlePattern(
        "Warrior",
        "rank",
    ),
    TitlePattern("Master", "rank", ("Grand Master", "GrandMaster")),
    TitlePattern("Grandmaster", "rank", ("Grand Master",)),
    TitlePattern(
        "Sage",
        "rank",
    ),
    TitlePattern(
        "Saint",
        "rank",
    ),
    TitlePattern(
        "Emperor",
        "rank",
    ),
    TitlePattern(
        "Empress",
        "rank",
    ),
    TitlePattern("Progenitor", "rank", ("Ancestor",)),
    TitlePattern(
        "Ancestor",
        "rank",
    ),
    TitlePattern(
        "Immortal",
        "rank",
    ),
    TitlePattern(
        "True Immortal",
        "rank",
    ),
    TitlePattern(
        "Golden Immortal",
        "rank",
    ),
    # Sect hierarchy / respect
    TitlePattern("Sect Leader", "rank", ("Sect Master", "SectMaster", "Patriarch")),
    TitlePattern("Elder", "rank", ("Grand Elder", "First Elder", "Elders")),
    TitlePattern(
        "Inner Disciple",
        "rank",
    ),
    TitlePattern(
        "Outer Disciple",
        "rank",
    ),
    TitlePattern(
        "Core Disciple",
        "rank",
    ),
    TitlePattern(
        "Personal Disciple",
        "rank",
    ),
    TitlePattern(
        "Pavilion Master",
        "rank",
    ),
    TitlePattern(
        "Hall Master",
        "rank",
    ),
    TitlePattern(
        "Peak Master",
        "rank",
    ),
    TitlePattern(
        "Protector",
        "rank",
    ),
    TitlePattern(
        "Protector of the Law",
        "rank",
    ),
    # Respect / family
    TitlePattern(
        "Senior", "respect", ("Senior Brother", "Senior Sister", "Senior Uncle", "Senior Aunt")
    ),
    TitlePattern("Junior", "respect", ("Junior Brother", "Junior Sister")),
    TitlePattern("Young Master", "family", ("Young Lord", "Young Lady", "Young Miss")),
    TitlePattern(
        "Eldest Young Master",
        "family",
    ),
    TitlePattern(
        "Second Young Master",
        "family",
    ),
    TitlePattern(
        "Third Young Master",
        "family",
    ),
    TitlePattern("Fairy", "respect", ("Fairy Sister", "Fairy Aunt", "Ice Fairy")),
    TitlePattern("Demon", "respect", ("Great Demon", "Heavenly Demon", "Demon King", "Demoness")),
    TitlePattern("Old Man", "respect", ("Old Lady", "Old Ancestor", "Old Monster")),
    TitlePattern("Lady", "family", ("Madam", "Matriarch")),
    TitlePattern(
        "Lord",
        "family",
    ),
    TitlePattern(
        "Princess",
        "family",
    ),
    TitlePattern(
        "Prince",
        "family",
    ),
]


# ---------------------------------------------------------------------------
# Organizations (sects / clans / guilds / …)
# ---------------------------------------------------------------------------

# Common suffix words that mark an organization.
ORG_SUFFIXES: tuple[str, ...] = (
    "Sect",
    "Clan",
    "Family",
    "Hall",
    "Pavilion",
    "Peak",
    "Mountain",
    "Valley",
    "Palace",
    "Temple",
    "Manor",
    "Castle",
    "City",
    "School",
    "Academy",
    "Tower",
    "Island",
    "Island of",
    "Court",
    "Guild",
    "Alliance",
    "Society",
    "Cult",
    "Holy Land",
    "Immortal Realm",
    "Empire",
    "Kingdom",
    "House",
)


# Seed organizations (canonical examples — the extractor will also pick up
# any "<Name> + suffix" pattern at runtime).
ORG_PATTERNS: list[OrgPattern] = [
    OrgPattern("Mount Hua Sect", "Sect", ("Mount Hua", "Mount Hua Sword Sect")),
    OrgPattern("Shaolin Temple", "Temple", ("Shaolin",)),
    OrgPattern("Wudang Sect", "Sect", ("Wudang",)),
    OrgPattern("Emei Sect", "Sect", ("Emei",)),
    OrgPattern("Beggar Sect", "Sect", ("Beggar's Sect", "Beggars' Sect")),
    OrgPattern("Tang Clan", "Clan", ("Tang Family",)),
    OrgPattern("Heavenly Demon Cult", "Cult", ("Demon Cult", "Heavenly Demon", "Demon Sect")),
    OrgPattern("Righteous Alliance", "Alliance", ("Righteous Path", "Righteous Sect")),
    OrgPattern("Unholy Union", "Alliance", ("Unholy Path",)),
    OrgPattern(
        "Hidden Dragon Hall",
        "Hall",
    ),
    OrgPattern(
        "Brocade Hall",
        "Hall",
    ),
    OrgPattern(
        "Immortal Sword Pavilion",
        "Pavilion",
    ),
    OrgPattern(
        "Plum Blossom Island",
        "Island",
    ),
]


# ---------------------------------------------------------------------------
# Location types
# ---------------------------------------------------------------------------

LOCATION_PATTERNS: list[LocationPattern] = [
    LocationPattern("Mount Hua", "Mountain", ("Mount Huashan",)),
    LocationPattern("Mount Kunlun", "Mountain", ("Kunlun Mountain",)),
    LocationPattern(
        "Mount Emei",
        "Mountain",
    ),
    LocationPattern(
        "Wudang Mountain",
        "Mountain",
    ),
    LocationPattern(
        "Central Plains",
        "Region",
    ),
    LocationPattern("Northern Wasteland", "Region", ("Northern Border",)),
    LocationPattern(
        "Southern Wasteland",
        "Region",
    ),
    LocationPattern("Jianghu", "Region", ("Rivers and Lakes", "The Jianghu")),
    LocationPattern(
        "Imperial City",
        "City",
    ),
    LocationPattern(
        "Heavenly Realm",
        "Realm",
    ),
    LocationPattern(
        "Demon Realm",
        "Realm",
    ),
]


# ---------------------------------------------------------------------------
# Relationship phrases
# ---------------------------------------------------------------------------

# (relationship_type, regex with two capture groups, group indices)
_RELATIONSHIP_TEMPLATES: list[tuple[str, str, tuple[int, int]]] = [
    (
        "master",
        r"(?P<s1>[\w\s]+?)\s+(?:is|was)\s+the\s+master\s+of\s+(?P<t1>[\w\s]+?)(?:[\.,;!\?]| and|\s*$)",
        (1, 2),
    ),
    ("master", r"(?P<s1>[\w\s]+?)'s\s+disciple\s+(?P<t1>[\w\s]+?)(?:[\.,;!\?]| and|\s*$)", (1, 2)),
    (
        "disciple",
        r"(?P<s1>[\w\s]+?)\s+(?:is|was)\s+(?:a|the)\s+disciple\s+of\s+(?P<t1>[\w\s]+?)(?:[\.,;!\?]| and|\s*$)",
        (1, 2),
    ),
    (
        "senior_brother",
        r"(?P<s1>[\w\s]+?)\s+(?:is|was)\s+the\s+senior\s+brother\s+of\s+(?P<t1>[\w\s]+?)(?:[\.,;!\?]| and|\s*$)",
        (1, 2),
    ),
    (
        "rival",
        r"(?P<s1>[\w\s]+?)\s+(?:is|was)\s+(?:a|the)\s+rival\s+of\s+(?P<t1>[\w\s]+?)(?:[\.,;!\?]| and|\s*$)",
        (1, 2),
    ),
    (
        "enemy",
        r"(?P<s1>[\w\s]+?)\s+(?:is|was)\s+(?:a|the)\s+(?:sworn\s+)?enemy\s+of\s+(?P<t1>[\w\s]+?)(?:[\.,;!\?]| and|\s*$)",
        (1, 2),
    ),
    (
        "ally",
        r"(?P<s1>[\w\s]+?)\s+(?:is|was)\s+(?:a|the)\s+ally\s+of\s+(?P<t1>[\w\s]+?)(?:[\.,;!\?]| and|\s*$)",
        (1, 2),
    ),
    (
        "friend",
        r"(?P<s1>[\w\s]+?)\s+(?:is|was)\s+(?:a\s+)?friend\s+of\s+(?P<t1>[\w\s]+?)(?:[\.,;!\?]| and|\s*$)",
        (1, 2),
    ),
    (
        "father",
        r"(?P<s1>[\w\s]+?)\s+(?:is|was)\s+the\s+father\s+of\s+(?P<t1>[\w\s]+?)(?:[\.,;!\?]| and|\s*$)",
        (1, 2),
    ),
    (
        "parent",
        r"(?P<s1>[\w\s]+?)'s\s+(?:son|daughter)\s+(?P<t1>[\w\s]+?)(?:[\.,;!\?]| and|\s*$)",
        (1, 2),
    ),
]

RELATIONSHIP_PHRASES: list[RelationshipPhrase] = [
    RelationshipPhrase(rel_type, re.compile(pattern, re.IGNORECASE), groups)
    for rel_type, pattern, groups in _RELATIONSHIP_TEMPLATES
]


# ---------------------------------------------------------------------------
# Capitalization heuristic — names are mostly 2-4 capitalized words
# ---------------------------------------------------------------------------

# A name candidate looks like 2-4 capitalized words, possibly with honorifics
NAME_TOKEN_PATTERN = re.compile(
    r"\b(?:[A-Z][a-zA-Z']+(?:\s+(?:de|von|of|the))?\s+){1,3}"
    r"[A-Z][a-zA-Z']+\b"
)


# ---------------------------------------------------------------------------
# Compiled lookup tables (for fast runtime access)
# ---------------------------------------------------------------------------


def _title_lookup() -> dict[str, TitlePattern]:
    """Map a normalized title string back to its pattern."""
    out: dict[str, TitlePattern] = {}
    for pat in TITLES:
        keys = {pat.title.lower(), *(a.lower() for a in pat.aliases)}
        for k in keys:
            out[k] = pat
    return out


TITLE_LOOKUP: dict[str, TitlePattern] = _title_lookup()


def _org_lookup() -> dict[str, OrgPattern]:
    out: dict[str, OrgPattern] = {}
    for pat in ORG_PATTERNS:
        keys = {pat.name.lower(), *(a.lower() for a in pat.aliases)}
        for k in keys:
            out[k] = pat
    return out


ORG_LOOKUP: dict[str, OrgPattern] = _org_lookup()


def _location_lookup() -> dict[str, LocationPattern]:
    out: dict[str, LocationPattern] = {}
    for pat in LOCATION_PATTERNS:
        keys = {pat.name.lower(), *(a.lower() for a in pat.aliases)}
        for k in keys:
            out[k] = pat
    return out


LOCATION_LOOKUP: dict[str, LocationPattern] = _location_lookup()


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def canonicalize_name(name: str) -> str:
    """Normalize a character name for dedup.

    Steps:
    * Strip newlines, carriage returns
    * Collapse internal whitespace
    * Strip trailing punctuation (., !, ?, ', ", ;, :)
    * Lowercase
    * Strip common honorifics that often precede the name ("Senior ", "Elder ", …)
    """
    if not name:
        return ""
    # Strip newlines and collapse whitespace
    cleaned = name.replace("\n", " ").replace("\r", " ")
    cleaned = " ".join(cleaned.split()).strip()
    # Strip trailing punctuation (keep internal hyphens/apostrophes)
    cleaned = cleaned.rstrip(".,!?\"';:")
    # Lowercase
    cleaned = cleaned.lower()
    # Strip leading honorifics (longest first to avoid partial matches)
    honorifics = sorted(TITLE_LOOKUP.keys(), key=len, reverse=True)
    for h in honorifics:
        if cleaned.startswith(h + " "):
            cleaned = cleaned[len(h) + 1 :]
    return cleaned


def is_org_suffix(word: str) -> bool:
    return word.lower() in {s.lower() for s in ORG_SUFFIXES}


def all_title_keys() -> list[str]:
    """Return the lowercase list of all title keys for matching."""
    return list(TITLE_LOOKUP.keys())


def all_org_keys() -> list[str]:
    return list(ORG_LOOKUP.keys())


def all_location_keys() -> list[str]:
    return list(LOCATION_LOOKUP.keys())


# ---------------------------------------------------------------------------
# Public dict-shaped accessors (used by extractors)
# ---------------------------------------------------------------------------


def titles_by_category() -> dict[str, list[str]]:
    """Group title names by category — useful for stat reporting."""
    out: dict[str, list[str]] = {}
    for pat in TITLES:
        out.setdefault(pat.category, []).append(pat.title)
    return out


# Re-export for type-hint completeness
__all__ = [
    "TitlePattern",
    "OrgPattern",
    "LocationPattern",
    "RelationshipPhrase",
    "TITLES",
    "ORG_SUFFIXES",
    "ORG_PATTERNS",
    "LOCATION_PATTERNS",
    "RELATIONSHIP_PHRASES",
    "TITLE_LOOKUP",
    "ORG_LOOKUP",
    "LOCATION_LOOKUP",
    "NAME_TOKEN_PATTERN",
    "canonicalize_name",
    "is_org_suffix",
    "all_title_keys",
    "all_org_keys",
    "all_location_keys",
    "titles_by_category",
]
