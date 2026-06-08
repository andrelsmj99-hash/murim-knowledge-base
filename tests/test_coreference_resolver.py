"""
Tests for the coreference resolver — resolves pronouns and title-based
references ("he", "the elder", "the sect master") to the most recent
character mention in the same scene.
"""

from app.processing.coreference_resolver import resolve_coreferences
from app.processing.ner import CharacterMention


def _make_mention(surface: str, canonical: str, start: int, end: int) -> CharacterMention:
    return CharacterMention(surface=surface, canonical=canonical, start=start, end=end)


class TestCoreferenceResolver:
    """Unit tests for resolve_coreferences()."""

    def test_empty_text(self):
        assert resolve_coreferences("", []) == []

    def test_none_text(self):
        assert resolve_coreferences(None, []) == []

    def test_no_mentions(self):
        text = "He walked across the courtyard."
        hits = resolve_coreferences(text, [])
        assert hits == []

    def test_pronoun_he_resolves_to_previous_character(self):
        text = "Lin Lei walked into the hall. He sat down quietly."
        mentions = [_make_mention("Lin Lei", "lin lei", 0, 7)]
        hits = resolve_coreferences(text, mentions)
        assert len(hits) >= 1
        assert any(h.resolved == "lin lei" for h in hits)
        assert any(h.surface.lower() == "he" for h in hits)

    def test_pronoun_she_resolves(self):
        text = "Mei Ling entered the room. She drew her sword."
        mentions = [_make_mention("Mei Ling", "mei ling", 0, 9)]
        hits = resolve_coreferences(text, mentions)
        assert len(hits) >= 1
        assert any(h.resolved == "mei ling" for h in hits)

    def test_pronoun_her_possessive_resolves(self):
        text = "Zhang Wei attacked. His blade shattered on impact."
        mentions = [_make_mention("Zhang Wei", "zhang wei", 0, 9)]
        hits = resolve_coreferences(text, mentions)
        assert len(hits) >= 1
        assert any(h.resolved == "zhang wei" for h in hits)

    def test_title_reference_the_elder(self):
        text = "Elder Lin Lei spoke coldly. The elder dismissed his disciple."
        mentions = [_make_mention("Elder Lin Lei", "lin lei", 0, 13)]
        hits = resolve_coreferences(text, mentions)
        assert len(hits) >= 1
        assert any(h.resolved == "lin lei" for h in hits)

    def test_title_reference_the_sect_master(self):
        text = "Sect Master Yun Chen governed the sect. The sect master was feared."
        mentions = [_make_mention("Sect Master Yun Chen", "yun chen", 0, 20)]
        hits = resolve_coreferences(text, mentions)
        assert any(h.resolved == "yun chen" for h in hits)

    def test_multiple_characters_tracks_most_recent(self):
        text = "Lin Lei spoke to Zhang Wei. Lin Lei smiled. He then left the hall."
        mentions = [
            _make_mention("Lin Lei", "lin lei", 0, 7),
            _make_mention("Zhang Wei", "zhang wei", 21, 30),
        ]
        hits = resolve_coreferences(text, mentions)
        # "He" after "Lin Lei smiled" should resolve to Lin Lei
        he_hits = [h for h in hits if h.surface.lower() == "he"]
        assert len(he_hits) >= 1
        assert he_hits[0].resolved == "lin lei"

    def test_pronoun_between_characters_resolves_to_first(self):
        text = "Di Shi arrived. He was angry. Qing Yan watched silently."
        mentions = [
            _make_mention("Di Shi", "di shi", 0, 6),
            _make_mention("Qing Yan", "qing yan", 30, 38),
        ]
        hits = resolve_coreferences(text, mentions)
        he_hits = [h for h in hits if h.surface.lower() == "he"]
        assert len(he_hits) >= 1
        assert he_hits[0].resolved == "di shi"

    def test_empty_text_with_mentions(self):
        assert resolve_coreferences("", [_make_mention("X", "x", 0, 1)]) == []

    def test_confidence_scores_are_valid(self):
        text = "Lin Lei entered. He smiled."
        mentions = [_make_mention("Lin Lei", "lin lei", 0, 7)]
        hits = resolve_coreferences(text, mentions)
        for h in hits:
            assert 0.0 <= h.confidence <= 1.0

    def test_no_pronouns_in_text(self):
        text = "The courtyard was quiet and still."
        mentions = [_make_mention("Lin Lei", "lin lei", 0, 7)]
        hits = resolve_coreferences(text, mentions)
        assert hits == []

    def test_coreference_hit_has_position(self):
        text = "Lin Lei arrived. He entered."
        mentions = [_make_mention("Lin Lei", "lin lei", 0, 7)]
        hits = resolve_coreferences(text, mentions)
        assert len(hits) >= 1
        for h in hits:
            assert h.start >= 0
            assert h.end > h.start

    def test_relative_pronoun_the_younger(self):
        text = "Zhang Wei stood beside his father. The younger bowed respectfully."
        mentions = [_make_mention("Zhang Wei", "zhang wei", 0, 9)]
        hits = resolve_coreferences(text, mentions)
        assert any(h.resolved == "zhang wei" for h in hits)

    def test_batch_resolution(self):
        texts = [
            "Lin Lei entered. He drew his sword.",
            "Zhang Wei watched. He remained silent.",
        ]
        mentions_list = [
            [_make_mention("Lin Lei", "lin lei", 0, 7)],
            [_make_mention("Zhang Wei", "zhang wei", 0, 9)],
        ]
        results = [resolve_coreferences(t, m) for t, m in zip(texts, mentions_list, strict=True)]
        assert results[0][0].resolved == "lin lei"
        assert results[1][0].resolved == "zhang wei"
