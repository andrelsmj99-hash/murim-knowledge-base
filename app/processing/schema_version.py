"""
NLP schema versioning for the Murim Knowledge Base.

Tracks the version of the NLP output schema (entity types, relationship
types, etc.) so that we can evolve the schema without breaking existing
data. Each NLP output is stamped with the schema version used to produce it.

Schema versions follow semantic versioning:
- MAJOR: breaking changes (removed fields, changed types)
- MINOR: new fields or relationship types (backward compatible)
- PATCH: bug fixes or documentation changes

Usage::

    from app.processing.schema_version import CURRENT_SCHEMA_VERSION, SchemaMeta

    meta = SchemaMeta(
        entity_types=["CHARACTER", "ORGANIZATION"],
        relationship_types=["master", "disciple"],
    )
    assert meta.version == CURRENT_SCHEMA_VERSION
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Current schema version
# ---------------------------------------------------------------------------

#: Current NLP output schema version (semver).
CURRENT_SCHEMA_VERSION: str = "1.0.0"

# ---------------------------------------------------------------------------
# Schema registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SchemaMeta:
    """Metadata describing a specific schema version."""

    version: str = CURRENT_SCHEMA_VERSION
    entity_types: tuple[str, ...] = ("CHARACTER",)
    relationship_types: tuple[str, ...] = (
        "master",
        "disciple",
        "senior_brother",
        "rival",
        "enemy",
        "ally",
        "friend",
        "father",
        "parent",
    )
    languages: tuple[str, ...] = ("en",)


# ---------------------------------------------------------------------------
# Version registry — keep all known schemas for migration checks
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, SchemaMeta] = {}


def register_schema(meta: SchemaMeta) -> None:
    """Register a schema version. Raises if the version already exists."""
    if meta.version in _REGISTRY:
        raise ValueError(f"Schema version {meta.version!r} already registered")
    _REGISTRY[meta.version] = meta


def get_schema(version: str) -> SchemaMeta:
    """Retrieve a registered schema by version string."""
    if version not in _REGISTRY:
        raise KeyError(f"Unknown schema version {version!r}. Available: {sorted(_REGISTRY)}")
    return _REGISTRY[version]


def list_schemas() -> list[str]:
    """Return all registered schema versions, sorted."""
    return sorted(_REGISTRY)


def is_compatible(current: str, required: str) -> bool:
    """Check if *current* schema satisfies *required* (major must match)."""
    cur = _parse(current)
    req = _parse(required)
    return cur[0] == req[0] and cur >= req


def _parse(v: str) -> tuple[int, int, int]:
    parts = v.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Invalid semver: {v!r}")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


# ---------------------------------------------------------------------------
# Bootstrap: register the current schema
# ---------------------------------------------------------------------------

register_schema(SchemaMeta())


__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "SchemaMeta",
    "register_schema",
    "get_schema",
    "list_schemas",
    "is_compatible",
]
