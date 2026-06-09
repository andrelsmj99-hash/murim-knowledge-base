"""Tests for app.processing.schema_version."""

from __future__ import annotations

import pytest

from app.processing.schema_version import (
    CURRENT_SCHEMA_VERSION,
    SchemaMeta,
    get_schema,
    is_compatible,
    list_schemas,
    register_schema,
)


class TestSchemaMeta:
    """Test SchemaMeta dataclass defaults."""

    def test_current_version_matches(self) -> None:
        meta = SchemaMeta()
        assert meta.version == CURRENT_SCHEMA_VERSION

    def test_default_entity_types(self) -> None:
        meta = SchemaMeta()
        assert "CHARACTER" in meta.entity_types

    def test_default_relationship_types(self) -> None:
        meta = SchemaMeta()
        assert "master" in meta.relationship_types
        assert "disciple" in meta.relationship_types

    def test_default_languages(self) -> None:
        meta = SchemaMeta()
        assert "en" in meta.languages

    def test_frozen(self) -> None:
        meta = SchemaMeta()
        with pytest.raises(AttributeError):
            meta.version = "2.0.0"  # type: ignore[misc]


class TestRegistry:
    """Test schema registration and lookup."""

    def test_get_current_schema(self) -> None:
        meta = get_schema(CURRENT_SCHEMA_VERSION)
        assert meta.version == CURRENT_SCHEMA_VERSION

    def test_list_schemas_includes_current(self) -> None:
        schemas = list_schemas()
        assert CURRENT_SCHEMA_VERSION in schemas

    def test_register_duplicate_raises(self) -> None:
        meta = SchemaMeta(version="99.0.0")
        register_schema(meta)
        with pytest.raises(ValueError, match="already registered"):
            register_schema(meta)

    def test_get_unknown_schema_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown schema version"):
            get_schema("0.0.0")


class TestCompatibility:
    """Test version compatibility checks."""

    def test_same_version_is_compatible(self) -> None:
        assert is_compatible("1.0.0", "1.0.0") is True

    def test_newer_minor_is_compatible(self) -> None:
        assert is_compatible("1.1.0", "1.0.0") is True

    def test_newer_patch_is_compatible(self) -> None:
        assert is_compatible("1.0.1", "1.0.0") is True

    def test_different_major_is_incompatible(self) -> None:
        assert is_compatible("2.0.0", "1.0.0") is False

    def test_older_version_is_incompatible(self) -> None:
        assert is_compatible("1.0.0", "1.1.0") is False

    def test_invalid_version_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid semver"):
            is_compatible("invalid", "1.0.0")


class TestSchemaStamp:
    """Test that NLP output can carry schema version metadata."""

    def test_extracted_entities_has_schema_version(self) -> None:
        from app.processing.ner import ExtractedEntities

        entities = ExtractedEntities()
        assert not hasattr(entities, "schema_version")

    def test_schema_meta_stamps_output(self) -> None:
        """Verify that a stamped output carries the correct version."""
        meta = SchemaMeta(version="1.2.3")
        output = {"entities": [], "schema_version": meta.version}
        assert output["schema_version"] == "1.2.3"
