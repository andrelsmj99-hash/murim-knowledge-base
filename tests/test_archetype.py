"""
Tests for character archetype classification feature.
"""
from __future__ import annotations

import uuid

import pytest

from app.core.entities import (
    CharacterArchetype,
    CombatStyle,
    NarrativeRole,
)
from app.models.character import Character as CharacterORM
from app.models.novel import Chapter as ChapterORM
from app.models.novel import Novel as NovelORM
from app.nlp.archetype_classifier import ArchetypeClassifier

# ---------------------------------------------------------------------------
# Unit tests for ArchetypeClassifier
# ---------------------------------------------------------------------------


class TestArchetypeClassifier:
    """Unit tests for the ArchetypeClassifier NLP component."""

    def test_classify_protagonist(self) -> None:
        classifier = ArchetypeClassifier()
        corpus = (
            "Lin Lei is the protagonist of this story. He is the main character "
            "and the hero. He fights against the villain and defeats many enemies. "
            "He uses a sword to strike down his opponents."
        )
        archetype = classifier.classify("char-1", corpus)
        assert isinstance(archetype, CharacterArchetype)
        assert archetype.narrative_role == NarrativeRole.PROTAGONIST
        assert archetype.character_id == "char-1"

    def test_classify_antagonist(self) -> None:
        classifier = ArchetypeClassifier()
        corpus = (
            "The villain was a terrible person. He was evil and caused destruction. "
            "He deceived many people and was the enemy of the protagonist."
        )
        archetype = classifier.classify("char-2", corpus)
        assert isinstance(archetype, CharacterArchetype)
        assert archetype.narrative_role == NarrativeRole.ANTAGONIST

    def test_classify_combat_styles(self) -> None:
        classifier = ArchetypeClassifier()
        sword_corpus = (
            "He wielded a sharp sword. The blade cut through the air. "
            "His sword technique was unparalleled."
        )
        archetype = classifier.classify("sword-char", sword_corpus)
        assert archetype.combat_style == CombatStyle.SWORD

        body_corpus = (
            "He punched with his fist. His palm struck the enemy. "
            "Fighting with bare fist was his style. He used punches and kicks."
        )
        archetype = classifier.classify("body-char", body_corpus)
        assert archetype.combat_style == CombatStyle.BODY

    def test_classify_empty_corpus(self) -> None:
        classifier = ArchetypeClassifier()
        archetype = classifier.classify("empty-char", "")
        assert isinstance(archetype, CharacterArchetype)
        assert archetype.role_confidence == 0.0
        assert archetype.combat_confidence == 0.0

    def test_classify_low_confidence(self) -> None:
        classifier = ArchetypeClassifier()
        # Random text with no strong signal words
        corpus = "The weather was nice that day. He walked to the market and bought some fruit."
        archetype = classifier.classify("low-char", corpus)
        assert archetype.role_confidence < 0.5 or archetype.combat_confidence < 0.5

    def test_trait_scores_are_valid(self) -> None:
        classifier = ArchetypeClassifier()
        corpus = "He is wise and intelligent. His knowledge is vast and deep."
        archetype = classifier.classify("trait-char", corpus)
        assert isinstance(archetype.trait_scores, dict)
        for _key, score in archetype.trait_scores.items():
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Integration tests for use cases
# ---------------------------------------------------------------------------


class TestClassifyCharacterArchetype:
    """Integration tests for the ClassifyCharacterArchetype use case."""

    def test_classify_with_chapters(
        self, sqlite_uow, seed_novel_and_characters, seed_chapters_with_character_mentions
    ):
        from app.core.use_cases import ClassifyCharacterArchetype

        char_repo = sqlite_uow.characters
        chapter_repo = sqlite_uow.chapters
        classifier = ArchetypeClassifier()

        chars = char_repo.list(limit=1)
        char = chars[0]

        uc = ClassifyCharacterArchetype(
            character_repository=char_repo,
            chapter_repository=chapter_repo,
            classifier=classifier,
        )
        archetype = uc.execute(char.id)

        assert isinstance(archetype, CharacterArchetype)
        assert archetype.character_id == char.id
        assert isinstance(archetype.narrative_role, NarrativeRole)
        assert isinstance(archetype.combat_style, CombatStyle)
        assert 0.0 <= archetype.role_confidence <= 1.0
        assert 0.0 <= archetype.combat_confidence <= 1.0

        # Verify it was persisted
        refreshed = char_repo.get(char.id)
        assert refreshed.archetype is not None

    def test_classify_nonexistent_character(self, sqlite_uow):
        from app.core.use_cases import ClassifyCharacterArchetype

        uc = ClassifyCharacterArchetype(
            character_repository=sqlite_uow.characters,
            chapter_repository=sqlite_uow.chapters,
            classifier=ArchetypeClassifier(),
        )
        with pytest.raises(ValueError, match="Character .* not found"):
            uc.execute(str(uuid.uuid4()))

    def test_classify_empty_corpus(
        self, sqlite_uow, seed_novel_and_characters
    ):
        from app.core.use_cases import ClassifyCharacterArchetype

        char_repo = sqlite_uow.characters
        chars = char_repo.list(limit=1)
        char = chars[0]

        uc = ClassifyCharacterArchetype(
            character_repository=char_repo,
            chapter_repository=sqlite_uow.chapters,
            classifier=ArchetypeClassifier(),
        )
        # No chapters exist, so corpus is empty
        archetype = uc.execute(char.id)
        assert archetype.role_confidence == 0.0
        assert archetype.combat_confidence == 0.0


class TestClassifyAllCharacters:
    """Integration tests for the ClassifyAllCharacters use case."""

    def test_classify_all(
        self, sqlite_uow, seed_novel_and_characters, seed_chapters_with_character_mentions
    ):
        from app.core.use_cases import ClassifyAllCharacters

        uc = ClassifyAllCharacters(
            character_repository=sqlite_uow.characters,
            chapter_repository=sqlite_uow.chapters,
            classifier=ArchetypeClassifier(),
        )
        results = uc.execute()

        assert len(results) > 0
        for char_id, archetype in results:
            assert isinstance(char_id, str)
            assert isinstance(archetype, CharacterArchetype)

    def test_classify_all_dominant_character(self, sqlite_uow, seed_dominant_character):
        from app.core.use_cases import ClassifyAllCharacters

        uc = ClassifyAllCharacters(
            character_repository=sqlite_uow.characters,
            chapter_repository=sqlite_uow.chapters,
            classifier=ArchetypeClassifier(),
        )
        results = uc.execute()

        assert len(results) == 1
        char_id, archetype = results[0]
        assert archetype.narrative_role == NarrativeRole.PROTAGONIST


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestArchetypeEndpoints:
    """Tests for the archetype API endpoints."""

    def _seed_via_api(self, client):
        """Seed a novel, characters, and chapters via the API."""
        # Create novel
        r = client.post(
            "/api/v1/novels",
            json={"title": "Test Novel", "author": "Test Author", "language": "en"},
        )
        assert r.status_code == 201
        novel_id = r.json()["id"]

        # Create chapters with character mentions
        for n in range(1, 4):
            content = {
                1: "Lin Lei awakened to a new world. The Dark Lord ruled the land with an iron fist. Using his sword, Lin Lei struck down many enemies.",
                2: "The Dark Lord was furious. He launched an attack on the village. Lin Lei stood his ground and fought back. With wisdom and intelligence, Lin Lei outsmarted the enemy.",
                3: "After a long battle, Lin Lei finally defeated the Dark Lord. The villagers celebrated. Lin Lei was hailed as the hero. His fists and sword techniques were legendary.",
            }[n]
            r = client.post(
                f"/api/v1/novels/{novel_id}/chapters",
                json={"chapter_number": n, "title": f"Chapter {n}", "content": content},
            )
            assert r.status_code == 201

        # Create characters
        r1 = client.post("/api/v1/characters", json={"name": "Lin Lei"})
        assert r1.status_code == 201
        char1_id = r1.json()["id"]

        r2 = client.post("/api/v1/characters", json={"name": "Dark Lord"})
        assert r2.status_code == 201
        char2_id = r2.json()["id"]

        return novel_id, char1_id, char2_id

    def test_classify_character_archetype(self, api_client):
        client, _ = api_client
        _, char1_id, _ = self._seed_via_api(client)

        r = client.post(f"/api/v1/characters/{char1_id}/classify")
        assert r.status_code == 200
        data = r.json()
        assert data["character_id"] == char1_id
        assert "narrative_role" in data
        assert "combat_style" in data
        assert "personality_traits" in data
        assert "role_confidence" in data
        assert "combat_confidence" in data

    def test_get_character_archetype(self, api_client):
        client, _ = api_client
        self._seed_via_api(client)

        r = client.get("/api/v1/characters")
        chars = r.json()["items"]
        assert len(chars) > 0
        char_id = chars[0]["id"]

        # No archetype yet
        r = client.get(f"/api/v1/characters/{char_id}/archetype")
        assert r.status_code == 200
        assert r.json() is None

    def test_classify_nonexistent_character(self, api_client):
        client, _ = api_client
        r = client.post(
            "/api/v1/characters/00000000-0000-0000-0000-000000000000/classify"
        )
        assert r.status_code == 404

    def test_get_archetype_nonexistent_character(self, api_client):
        client, _ = api_client
        r = client.get(
            "/api/v1/characters/00000000-0000-0000-0000-000000000000/archetype"
        )
        assert r.status_code == 404

    def test_classify_all_characters(self, api_client):
        client, _ = api_client
        self._seed_via_api(client)

        r = client.post("/api/v1/characters/classify-all")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "classified" in data
        assert data["total"] == data["classified"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def seed_novel_and_characters(sqlite_uow):
    """Seed a novel and some characters for archetype testing."""
    novel = NovelORM(
        title="Test Novel",
        author="Test Author",
        language="en",
    )
    sqlite_uow.session.add(novel)
    sqlite_uow.session.flush()

    char1 = CharacterORM(
        name="Lin Lei",
        canonical_name="lin lei",
        gender="male",
        description="The protagonist of the story.",
    )
    sqlite_uow.session.add(char1)

    char2 = CharacterORM(
        name="Dark Lord",
        canonical_name="dark lord",
        gender="male",
        description="The main antagonist.",
    )
    sqlite_uow.session.add(char2)
    sqlite_uow.session.flush()

    # Refresh to get IDs
    sqlite_uow.session.refresh(novel)
    sqlite_uow.session.refresh(char1)
    sqlite_uow.session.refresh(char2)

    return (
        NovelORM(id=novel.id, title=novel.title, author=novel.author, language=novel.language),
        CharacterORM(id=char1.id, name=char1.name, canonical_name=char1.canonical_name),
        CharacterORM(id=char2.id, name=char2.name, canonical_name=char2.canonical_name),
    )


@pytest.fixture
def seed_chapters_with_character_mentions(sqlite_uow, seed_novel_and_characters):
    """Seed chapters that mention characters by name."""
    novel, char1, char2 = seed_novel_and_characters

    chapters_data = [
        {
            "chapter_number": 1,
            "title": "The Beginning",
            "content": (
                f"{char1.name} awakened to a new world. "
                f"The {char2.name} ruled the land with an iron fist. "
                f"{char1.name} decided to fight back against the {char2.name}. "
                f"Using his sword, {char1.name} struck down many enemies."
            ),
        },
        {
            "chapter_number": 2,
            "title": "The Battle",
            "content": (
                f"The {char2.name} was furious. He launched an attack on the village. "
                f"{char1.name} stood his ground and fought back. "
                f"With wisdom and intelligence, {char1.name} outsmarted the enemy."
            ),
        },
        {
            "chapter_number": 3,
            "title": "Victory",
            "content": (
                f"After a long battle, {char1.name} finally defeated the {char2.name}. "
                f"The villagers celebrated. {char1.name} was hailed as the hero. "
                f"His fists and sword techniques were legendary."
            ),
        },
    ]

    for data in chapters_data:
        chapter = ChapterORM(
            id=uuid.uuid4(),
            novel_id=uuid.UUID(str(novel.id)),
            chapter_number=data["chapter_number"],
            title=data["title"],
            content=data["content"],
            word_count=len(data["content"].split()),
        )
        sqlite_uow.session.add(chapter)
    sqlite_uow.session.flush()


@pytest.fixture
def seed_dominant_character(sqlite_uow):
    """Seed a novel with a single dominant character for low-corpus testing."""
    novel = NovelORM(
        title="Solo Hero",
        author="Test Author",
        language="en",
    )
    sqlite_uow.session.add(novel)
    sqlite_uow.session.flush()

    char = CharacterORM(
        name="Solo",
        canonical_name="solo",
        gender="male",
        description="The only character.",
    )
    sqlite_uow.session.add(char)
    sqlite_uow.session.flush()

    # Add chapters mentioning only this character
    for i in range(3):
        chapter = ChapterORM(
            id=uuid.uuid4(),
            novel_id=uuid.UUID(str(novel.id)),
            chapter_number=i + 1,
            title=f"Chapter {i + 1}",
            content=(
                "Solo is the main character. He is the hero of this story. "
                "Solo fights with his fists and his sword. "
                "His wisdom and intelligence guide him through challenges."
            ),
        )
        sqlite_uow.session.add(chapter)
    sqlite_uow.session.flush()
