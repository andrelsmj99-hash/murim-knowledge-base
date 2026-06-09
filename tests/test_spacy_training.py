"""Tests for app.processing.spacy_training."""

from __future__ import annotations

import json
from pathlib import Path

from app.processing.spacy_training import export_spacy_format, generate_training_data


class TestGenerateTrainingData:
    """Test synthetic training data generation."""

    def test_generates_requested_count(self) -> None:
        data = generate_training_data(n_samples=10, seed=42)
        assert len(data) == 10

    def test_each_example_has_text_and_entities(self) -> None:
        data = generate_training_data(n_samples=5, seed=42)
        for text, ents in data:
            assert isinstance(text, str)
            assert len(text) > 0
            assert "entities" in ents
            assert isinstance(ents["entities"], list)

    def test_entities_are_valid_spans(self) -> None:
        data = generate_training_data(n_samples=20, seed=42)
        for text, ents in data:
            for start, end, label in ents["entities"]:
                assert 0 <= start < end <= len(text)
                assert label in {"PERSON", "TITLE", "ORG", "LOCATION"}
                substring = text[start:end]
                assert len(substring) > 0

    def test_entities_are_sorted_by_start(self) -> None:
        data = generate_training_data(n_samples=20, seed=42)
        for _, ents in data:
            starts = [s for s, _, _ in ents["entities"]]
            assert starts == sorted(starts)

    def test_no_overlapping_entities(self) -> None:
        data = generate_training_data(n_samples=20, seed=42)
        for _, ents in data:
            spans = [(s, e) for s, e, _ in ents["entities"]]
            for i, (s1, e1) in enumerate(spans):
                for s2, e2 in spans[i + 1 :]:
                    assert e1 <= s2 or e2 <= s1, f"Overlap: ({s1},{e1}) and ({s2},{e2})"

    def test_deterministic_with_seed(self) -> None:
        data1 = generate_training_data(n_samples=5, seed=123)
        data2 = generate_training_data(n_samples=5, seed=123)
        assert data1 == data2

    def test_different_seeds_produce_different_data(self) -> None:
        data1 = generate_training_data(n_samples=10, seed=1)
        data2 = generate_training_data(n_samples=10, seed=2)
        assert data1 != data2


class TestExportSpaCyFormat:
    """Test JSONL export for spaCy training."""

    def test_creates_file(self, tmp_path: Path) -> None:
        data = generate_training_data(n_samples=5, seed=42)
        out = tmp_path / "train.jsonl"
        export_spacy_format(data, str(out))
        assert out.exists()

    def test_one_line_per_example(self, tmp_path: Path) -> None:
        data = generate_training_data(n_samples=10, seed=42)
        out = tmp_path / "train.jsonl"
        export_spacy_format(data, str(out))
        lines = out.read_text().strip().split("\n")
        assert len(lines) == 10

    def test_valid_json_per_line(self, tmp_path: Path) -> None:
        data = generate_training_data(n_samples=5, seed=42)
        out = tmp_path / "train.jsonl"
        export_spacy_format(data, str(out))
        for line in out.read_text().strip().split("\n"):
            obj = json.loads(line)
            assert "text" in obj
            assert "entities" in obj
