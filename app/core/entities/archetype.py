"""
Character archetype domain entities.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class NarrativeRole(str, Enum):
    """The role a character plays in the narrative."""

    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    MENTOR = "mentor"
    RIVAL = "rival"
    ALLY = "ally"
    BACKGROUND = "background"


class CombatStyle(str, Enum):
    """The primary combat style of a character."""

    SWORD = "sword"
    BODY = "body"
    POISON = "poison"
    SPEED = "speed"
    QI_INTERNAL = "qi_internal"
    RANGED = "ranged"
    SUPPORT = "support"
    UNKNOWN = "unknown"


class PersonalityTrait(str, Enum):
    """Personality traits commonly found in Murim characters."""

    ARROGANT = "arrogant"
    COLD = "cold"
    LOYAL = "loyal"
    MYSTERIOUS = "mysterious"
    AMBITIOUS = "ambitious"
    PROTECTIVE = "protective"
    TRAITOR = "traitor"


@dataclass
class CharacterArchetype:
    """Complete archetype classification for a character."""

    character_id: str
    narrative_role: NarrativeRole = NarrativeRole.BACKGROUND
    combat_style: CombatStyle = CombatStyle.UNKNOWN
    personality_traits: list[PersonalityTrait] = field(default_factory=list)
    role_confidence: float = 0.0
    combat_confidence: float = 0.0
    trait_scores: dict[str, float] = field(default_factory=dict)
    classified_by: str = "rules"  # "rules" | "llm" | "manual"

    def __post_init__(self):
        # Ensure confidence values are clamped to [0.0, 1.0]
        self.role_confidence = max(0.0, min(1.0, self.role_confidence))
        self.combat_confidence = max(0.0, min(1.0, self.combat_confidence))
        # Clamp trait scores
        for k, v in self.trait_scores.items():
            self.trait_scores[k] = max(0.0, min(1.0, v))


__all__ = [
    "NarrativeRole",
    "CombatStyle",
    "PersonalityTrait",
    "CharacterArchetype",
]