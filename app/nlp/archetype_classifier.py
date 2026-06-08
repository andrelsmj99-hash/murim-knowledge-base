"""
Archetype classifier for Murim/Wuxia characters using NLP techniques.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from typing import Any

from app.core.entities import (
    CharacterArchetype,
    CombatStyle,
    NarrativeRole,
    PersonalityTrait,
)


class ArchetypeClassifier:
    """Classifies character archetypes based on text analysis."""

    def __init__(self):
        """Initialize the classifier with Murim/Wuxia vocabulary patterns."""
        # Narrative role keywords
        self.narrative_keywords = {
            NarrativeRole.PROTAGONIST: [
                "main character",
                "mc",
                "hero",
                "protagonist",
                "chosen one",
                "destined",
                "fated",
                "reincarnated",
                "transmigrated",
                "cultivation",
                "breakthrough",
                "realm",
                "stage",
                "level",
                "power",
                "strength",
                "destiny",
                "chosen",
                "legendary",
                "heroic",
                "brave",
                "valiant",
                "champion",
                "savior",
            ],
            NarrativeRole.ANTAGONIST: [
                "villain",
                "antagonist",
                "evil",
                "malicious",
                "vindictive",
                "cruel",
                "tyrant",
                "despot",
                "oppressor",
                "ruthless",
                "rival",
                "enemy",
                "foe",
                "adversary",
                "menacing",
                "sinister",
                "malevolent",
                "vile",
                "wicked",
            ],
            NarrativeRole.MENTOR: [
                "master",
                "teacher",
                "elder",
                "senior",
                "sage",
                "grandmaster",
                "patriarch",
                "matriarch",
                "ancestor",
                "guide",
                "instructor",
                "tutor",
                "mentor",
                "wise",
                "ancient",
                "venerable",
                "experienced",
                "knowledgeable",
                "sage",
            ],
            NarrativeRole.RIVAL: [
                "rival",
                "competitor",
                "opponent",
                "challenger",
                "contestant",
                "duelist",
                "adversary",
                "foe",
                "nemesis",
                "opponent",
                "challenger",
            ],
            NarrativeRole.ALLY: [
                "ally",
                "companion",
                "friend",
                "partner",
                "comrade",
                "confidant",
                "ally",
                "supporter",
                "follower",
                "disciple",
                "student",
                "apprentice",
            ],
            NarrativeRole.BACKGROUND: [
                "background",
                "minor",
                "supporting",
                "extra",
                "passerby",
                "citizen",
                "villager",
                "commoner",
                "servant",
                "guard",
                "soldier",
                "merchant",
            ],
        }

        # Combat style keywords
        self.combat_keywords = {
            CombatStyle.SWORD: [
                "sword",
                "blade",
                "katana",
                "jian",
                "dao",
                "saber",
                "edge",
                "cut",
                "slash",
                "thrust",
                "swordsmanship",
                "blade technique",
                "sword technique",
            ],
            CombatStyle.BODY: [
                "fist",
                "palm",
                "finger",
                "kick",
                "punch",
                "body",
                "martial",
                "barehanded",
                "unarmed",
                "fist technique",
                "palm strike",
                "finger strike",
                "body technique",
                "martial arts",
                "boxing",
                "kung fu",
            ],
            CombatStyle.POISON: [
                "poison",
                "toxin",
                "venom",
                "poisonous",
                "toxic",
                "venomous",
                "deadly",
                "lethal",
                "noxious",
                "venom technique",
                "poison technique",
            ],
            CombatStyle.SPEED: [
                "swift",
                "speed",
                "fast",
                "quick",
                "agile",
                "nimble",
                "fleet",
                "rapid",
                "velocity",
                "lightning",
                "flash",
                "blur",
                "speed technique",
            ],
            CombatStyle.QI_INTERNAL: [
                "qi",
                "chi",
                "inner",
                "internal",
                "energy",
                "spiritual",
                "cultivation",
                "spirit",
                "mana",
                "spirit force",
                "inner energy",
                "breathing",
                "meditation",
            ],
            CombatStyle.RANGED: [
                "ranged",
                "distance",
                "remote",
                "bow",
                "arrow",
                "projectile",
                "throwing",
                "shooting",
                "distance attack",
                "ranged technique",
            ],
            CombatStyle.SUPPORT: [
                "support",
                "heal",
                "healing",
                "cure",
                "protect",
                "shield",
                "defend",
                "barrier",
                "protective",
                "auxiliary",
                "buff",
                "support technique",
            ],
            CombatStyle.UNKNOWN: ["unknown", "mysterious", "unclear", "ambiguous"],
        }

        # Personality trait keywords
        self.personality_keywords = {
            PersonalityTrait.ARROGANT: [
                "arrogant",
                "proud",
                "haughty",
                "conceited",
                "egotistical",
                "vain",
                "boastful",
                "snobbish",
                "supercilious",
                "overconfident",
                "smug",
            ],
            PersonalityTrait.COLD: [
                "cold",
                "distant",
                "aloof",
                "detached",
                "emotionless",
                "stoic",
                "icy",
                "frosty",
                "chilly",
                "unemotional",
                "apathetic",
            ],
            PersonalityTrait.LOYAL: [
                "loyal",
                "faithful",
                "devoted",
                "dedicated",
                "committed",
                "steadfast",
                "reliable",
                "trustworthy",
                "dependable",
                "allegiant",
                "true",
            ],
            PersonalityTrait.MYSTERIOUS: [
                "mysterious",
                "enigmatic",
                "cryptic",
                "secretive",
                "mystifying",
                "puzzling",
                "obscure",
                "ambiguous",
                "shadowy",
                "inscrutable",
            ],
            PersonalityTrait.AMBITIOUS: [
                "ambitious",
                "driven",
                "determined",
                "goal-oriented",
                "aspiring",
                "motivated",
                "eager",
                "zealous",
                "aspirational",
                "goal-focused",
            ],
            PersonalityTrait.PROTECTIVE: [
                "protective",
                "guardian",
                "defender",
                "shield",
                "caretaker",
                "watchful",
                "vigilant",
                "guarding",
                "shielding",
                "defending",
            ],
            PersonalityTrait.TRAITOR: [
                "traitor",
                "betrayer",
                "deceiver",
                "backstabber",
                "turncoat",
                "double-crosser",
                "spy",
                "infiltrator",
                "saboteur",
                "mole",
            ],
        }

        # Flatten all keywords for preprocessing
        self.all_keywords = []
        all_kw_dicts: list[Mapping[Any, list[str]]] = [
            self.narrative_keywords,
            self.combat_keywords,
            self.personality_keywords,
        ]
        for keywords in all_kw_dicts:
            for category_keywords in keywords.values():
                if isinstance(category_keywords, list):
                    self.all_keywords.extend(category_keywords)
                else:
                    for keyword_list in category_keywords:
                        self.all_keywords.extend(category_keywords[keyword_list])

    def _preprocess_text(self, text: str) -> str:
        """Clean and normalize text for keyword matching."""
        # Convert to lowercase
        text = text.lower()
        # Remove extra whitespace
        text = " ".join(text.split())
        return text

    def _calculate_confidence(self, matches: int, total_words: int) -> float:
        """Calculate confidence score based on keyword matches."""
        if total_words == 0:
            return 0.0
        return min(1.0, matches / total_words)

    def _normalize_text(self, text: str) -> list[str]:
        """Normalize text into words for analysis."""
        # Simple tokenization
        words = re.findall(r"\b\w+\b", self._preprocess_text(text))
        return words

    def classify(self, character_id: str, text_corpus: str) -> CharacterArchetype:
        """
        Classify a character's archetype based on text analysis.

        Args:
            character_id: The ID of the character to classify
            text_corpus: Text content to analyze for classification

        Returns:
            CharacterArchetype with classification results
        """
        # Normalize the text
        words = self._normalize_text(text_corpus)
        word_count = len(words)

        if word_count == 0:
            # Return default archetype for empty corpus
            return CharacterArchetype(
                character_id=character_id,
                narrative_role=NarrativeRole.BACKGROUND,
                combat_style=CombatStyle.UNKNOWN,
                personality_traits=[],
                role_confidence=0.0,
                combat_confidence=0.0,
                trait_scores={},
                classified_by="rules",
            )

        # Count keyword matches for each category
        word_counter = Counter(words)

        # Classify narrative role
        narrative_scores = {}
        for role, keywords in self.narrative_keywords.items():
            matches = sum(word_counter.get(keyword.lower(), 0) for keyword in keywords)
            narrative_scores[role] = matches / max(1, word_count)  # Normalize

        # Find best narrative role
        best_narrative_role = max(narrative_scores.items(), key=lambda x: x[1])
        narrative_role = best_narrative_role[0]
        role_confidence = best_narrative_role[1]

        # Classify combat style
        combat_scores = {}
        for style, keywords in self.combat_keywords.items():
            matches = sum(word_counter.get(keyword.lower(), 0) for keyword in keywords)
            combat_scores[style] = matches / max(1, word_count)  # Normalize

        # Find best combat style
        best_combat_style = max(combat_scores.items(), key=lambda x: x[1])
        combat_style = best_combat_style[0]
        combat_confidence = best_combat_style[1]

        # Classify personality traits
        personality_traits = []
        trait_scores = {}

        for trait, keywords in self.personality_keywords.items():
            matches = sum(word_counter.get(keyword.lower(), 0) for keyword in keywords)
            if matches > 0:  # Only include traits with some evidence
                trait_scores[trait] = matches / max(1, word_count)
                if trait_scores[trait] > 0.01:  # Threshold for inclusion
                    personality_traits.append(trait)

        # Create the archetype
        return CharacterArchetype(
            character_id=character_id,
            narrative_role=narrative_role,
            combat_style=combat_style,
            personality_traits=personality_traits,
            role_confidence=role_confidence,
            combat_confidence=combat_confidence,
            trait_scores={k.value: v for k, v in trait_scores.items()},
            classified_by="rules",
        )
