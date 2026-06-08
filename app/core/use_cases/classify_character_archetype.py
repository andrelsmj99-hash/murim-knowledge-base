"""
Use cases for character archetype classification.
"""
from __future__ import annotations

from app.core.entities import CharacterArchetype
from app.core.interfaces import IChapterRepository, ICharacterRepository
from app.nlp.archetype_classifier import ArchetypeClassifier


class ClassifyCharacterArchetype:
    """Use case for classifying a single character's archetype."""

    def __init__(
        self,
        character_repository: ICharacterRepository,
        chapter_repository: IChapterRepository,
        classifier: ArchetypeClassifier,
    ):
        self.character_repository = character_repository
        self.chapter_repository = chapter_repository
        self.classifier = classifier

    def execute(self, character_id: str) -> CharacterArchetype:
        """
        Classify a character's archetype based on all chapters where they appear.

        Args:
            character_id: The ID of the character to classify

        Returns:
            CharacterArchetype with classification results
        """
        # Get the character
        character = self.character_repository.get(character_id)
        if not character:
            raise ValueError(f"Character {character_id} not found")

        # Get all chapters where this character appears by name or aliases
        chapters = self.chapter_repository.get_chapters_by_character(character_id)

        # Build corpus from all relevant chapters
        corpus_parts: list[str] = []
        for chapter in chapters:
            if chapter.title:
                corpus_parts.append(chapter.title)
            if chapter.content:
                corpus_parts.append(chapter.content)

        corpus = " ".join(corpus_parts)

        # Classify the character
        archetype = self.classifier.classify(character_id, corpus)

        # Persist the archetype
        self.character_repository.set_archetype(character_id, archetype)

        return archetype


class ClassifyAllCharacters:
    """Use case for classifying all characters' archetypes in batch."""

    def __init__(
        self,
        character_repository: ICharacterRepository,
        chapter_repository: IChapterRepository,
        classifier: ArchetypeClassifier,
    ):
        self.character_repository = character_repository
        self.chapter_repository = chapter_repository
        self.classifier = classifier

    def execute(self) -> list[tuple[str, CharacterArchetype]]:
        """
        Classify all characters in the database.

        Returns:
            List of (character_id, CharacterArchetype) tuples
        """
        results: list[tuple[str, CharacterArchetype]] = []
        characters = self.character_repository.list(limit=10_000)

        for character in characters:
            # Get all chapters where this character appears
            chapters = self.chapter_repository.get_chapters_by_character(character.id)

            # Build corpus from all relevant chapters
            corpus_parts: list[str] = []
            for chapter in chapters:
                if chapter.title:
                    corpus_parts.append(chapter.title)
                if chapter.content:
                    corpus_parts.append(chapter.content)

            corpus = " ".join(corpus_parts)

            # Classify the character
            archetype = self.classifier.classify(character.id, corpus)

            # Persist the archetype
            self.character_repository.set_archetype(character.id, archetype)

            results.append((character.id, archetype))

        return results
