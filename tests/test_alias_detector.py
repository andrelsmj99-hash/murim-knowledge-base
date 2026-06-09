"""
Tests for the alias detector — extracts aliases from context phrases
like "also known as", "whose real name was", "formerly known as".
"""

from app.processing.alias_detector import detect_aliases


class TestAliasDetector:
    """Unit tests for detect_aliases()."""

    def test_also_known_as(self):
        text = "The mysterious figure was also known as the Shadow Emperor."
        hits = detect_aliases(text)
        assert len(hits) >= 1
        assert any("shadow emperor" in h.alias.lower() for h in hits)

    def test_whose_real_name_was(self):
        text = "Wei Changqing, whose real name was Wei Sheng, smiled coldly."
        hits = detect_aliases(text)
        assert len(hits) >= 1
        # Should detect "Wei Changqing" as alias for "Wei Sheng" or vice versa
        real_names = {h.real_name.lower() for h in hits}
        aliases = {h.alias.lower() for h in hits}
        assert "wei sheng" in real_names or "wei sheng" in aliases

    def test_formerly_known_as(self):
        text = "He was formerly known as the Demon King before his reincarnation."
        hits = detect_aliases(text)
        assert len(hits) >= 1
        assert any(
            "demon king" in h.alias.lower() or "demon king" in h.real_name.lower() for h in hits
        )

    def test_once_called(self):
        text = "The old man was once called the Sword Saint."
        hits = detect_aliases(text)
        assert len(hits) >= 1
        assert any(
            "sword saint" in h.alias.lower() or "sword saint" in h.real_name.lower() for h in hits
        )

    def test_born_as(self):
        text = "Born as Li Tian, he later became known as the Heavenly Sovereign."
        hits = detect_aliases(text)
        assert len(hits) >= 1
        real_names = {h.real_name.lower() for h in hits}
        aliases = {h.alias.lower() for h in hits}
        assert "li tian" in real_names or "li tian" in aliases

    def test_known_as(self):
        text = "Iron Fist, known as the Crimson Blade, trained silently."
        hits = detect_aliases(text)
        assert len(hits) >= 1
        assert any("iron fist" in h.real_name.lower() for h in hits)
        assert any("crimson blade" in h.alias.lower() for h in hits)

    def test_multiple_aliases_same_character(self):
        text = (
            "Zhang Wei, also known as the Blade Demon, "
            "whose real name was Zhang Tianlong, was feared across the Jianghu."
        )
        hits = detect_aliases(text)
        assert len(hits) >= 2

    def test_empty_text(self):
        assert detect_aliases("") == []
        assert detect_aliases(None) == []

    def test_no_aliases_in_text(self):
        text = "The old sect master sat quietly on his throne, contemplating the future."
        hits = detect_aliases(text)
        assert hits == []

    def test_alias_confidence_score(self):
        text = "He was also known as the Sword Immortal."
        hits = detect_aliases(text)
        assert len(hits) >= 1
        for h in hits:
            assert 0.0 <= h.confidence <= 1.0
            assert h.confidence > 0.5  # High confidence for clear patterns

    def test_alias_hit_has_context(self):
        text = "The elder, whose true name was lost to history, was called the Old Monster."
        hits = detect_aliases(text)
        assert len(hits) >= 1
        for h in hits:
            assert h.context  # Context should be non-empty
            assert len(h.context) > 0

    def test_alias_hit_canonical_names(self):
        text = "Chen Lin, also known as the Crimson Blade, trained under Elder Zhao."
        hits = detect_aliases(text)
        assert len(hits) >= 1
        for h in hits:
            # Murim title-prefix patterns produce hits with empty real_name
            if h.real_name:
                assert h.canonical_real_name  # Should be normalized
            assert h.canonical_alias  # Should always be normalized

    def test_alias_with_title_prefix(self):
        text = "Elder Lin Lei was also known as the Sage of the Northern Gate."
        hits = detect_aliases(text)
        assert len(hits) >= 1

    def test_alias_complex_sentence(self):
        text = (
            "The man who once bore the name Li Qiang, "
            "formerly known as the Thunder Emperor, "
            "now lived as a humble merchant."
        )
        hits = detect_aliases(text)
        assert len(hits) >= 1


class TestAliasDetectorIntegration:
    """Integration tests with the extraction pipeline."""

    def test_alias_in_extracted_entities(self):
        """Alias detector should add aliases to ChapterExtraction."""
        from app.core.use_cases.extract_entities import ExtractEntitiesUseCase

        text = (
            "Wei Sheng, also known as the Sword Sovereign, "
            "trained at Mount Hua Sect. His real name was Wei Tianlong."
        )
        use_case = ExtractEntitiesUseCase()
        result = use_case.execute(text)

        # Should have extracted aliases
        assert len(result.aliases) >= 1

    def test_alias_empty_corpus(self):
        """Empty corpus should produce no aliases."""
        from app.core.use_cases.extract_entities import ExtractEntitiesUseCase

        use_case = ExtractEntitiesUseCase()
        result = use_case.execute("")
        assert result.aliases == []

    def test_alias_dominant_character(self):
        """Character mentioned multiple times with alias should produce alias hit."""
        from app.core.use_cases.extract_entities import ExtractEntitiesUseCase

        text = (
            "Lin Feng was also known as the Dragon Emperor. "
            "Lin Feng trained day and night. "
            "The Dragon Emperor was feared throughout the land."
        )
        use_case = ExtractEntitiesUseCase()
        result = use_case.execute(text)
        assert len(result.aliases) >= 1
