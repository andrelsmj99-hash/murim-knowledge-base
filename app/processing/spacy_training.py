"""
Training data generator for a custom Murim spaCy NER model.

Generates synthetic training data from the existing pattern tables
(TITLES, ORG_PATTERNS, LOCATION_PATTERNS) so we can fine-tune a
spaCy model on domain-specific entities.

Usage::

    from app.processing.spacy_training import generate_training_data

    data = generate_training_data(n_samples=500)
    # data is a list of (text, {"entities": [(start, end, label), ...]})
"""

from __future__ import annotations

import random
from typing import Any

from app.processing.patterns import (
    LOCATION_PATTERNS,
    ORG_PATTERNS,
    TITLES,
)

# ---------------------------------------------------------------------------
# Synthetic text templates
# ---------------------------------------------------------------------------

# Murim-themed sentence templates with {name}, {org}, {location}, {title} slots.
_TEMPLATES: list[str] = [
    "{name} joined the {org}.",
    "The {title} {name} guarded the {location}.",
    "{name} was a disciple of the {org}.",
    "At the {location}, {name} trained under the {title}.",
    "The {org} controlled the {location} for centuries.",
    "{title} {name} challenged the elders of the {org}.",
    "In the {location}, {name} discovered a hidden technique.",
    "The {org} and the {title} {name} formed an alliance.",
    "{name} left the {org} to travel to the {location}.",
    "The {title} {name} defended the {location} from invaders.",
    "{name} was the {title} of the {org}.",
    "At the {location}, {name} fought the {title}.",
    "The {org} recruited {name} from the {location}.",
    "{title} {name} trained at the {location}.",
    "The {location} was sacred to the {org}.",
    "{name} rose to become {title} of the {org}.",
    "The {title} {name} protected the {location}.",
    "{org} sent {name} to the {location}.",
    "{name} challenged the {title} at the {location}.",
    "The {org} was founded by {title} {name} at the {location}.",
]

# Character name pools (domain-appropriate)
_MALE_NAMES = [
    "Wei Feng",
    "Lin Lei",
    "Chen Tian",
    "Zhang Wei",
    "Liu Ming",
    "Wang Hao",
    "Li Xuan",
    "Zhao Yun",
    "Sun Jian",
    "Ma Chao",
    "Huang Zhong",
    "Guan Yu",
    "Zhang Fei",
    "Liu Bei",
    "Cao Cao",
    "Sima Yi",
    "Zhuge Liang",
    "Jiang Wei",
    "Deng Ai",
    "Zhong Hui",
]

_FEMALE_NAMES = [
    "Lin Mei",
    "Chen Xue",
    "Zhang Yun",
    "Liu Yan",
    "Wang Ling",
    "Li Hua",
    "Zhao Die",
    "Sun Shang",
    "Ma Qing",
    "Huang Yue",
]

_NAMES = _MALE_NAMES + _FEMALE_NAMES


def _pick_name() -> str:
    return random.choice(_NAMES)


def _pick_org() -> str:
    return random.choice(ORG_PATTERNS).name


def _pick_location() -> str:
    return random.choice(LOCATION_PATTERNS).name


def _pick_title() -> str:
    return random.choice(TITLES).title


def _fill_template(template: str) -> str:
    return template.format(
        name=_pick_name(),
        org=_pick_org(),
        location=_pick_location(),
        title=_pick_title(),
    )


def _find_entity_span(text: str, entity: str) -> tuple[int, int] | None:
    """Find the character span of *entity* in *text* (case-insensitive)."""
    idx = text.lower().find(entity.lower())
    if idx == -1:
        return None
    return (idx, idx + len(entity))


def _label_for_entity(entity: str) -> str | None:
    """Determine the NER label for an entity string."""
    # Check titles
    for t in TITLES:
        if entity.lower() == t.title.lower():
            return "TITLE"
    # Check orgs
    for o in ORG_PATTERNS:
        if entity.lower() == o.name.lower() or entity.lower() in {a.lower() for a in o.aliases}:
            return "ORG"
    # Check locations
    for loc in LOCATION_PATTERNS:
        if entity.lower() == loc.name.lower() or entity.lower() in {a.lower() for a in loc.aliases}:
            return "LOCATION"
    # Check names (all names are PERSON)
    for n in _NAMES:
        if entity.lower() == n.lower():
            return "PERSON"
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_training_data(
    n_samples: int = 500,
    seed: int | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    """Generate synthetic spaCy training data.

    Returns a list of ``(text, annotations)`` tuples where *annotations*
    contains an ``"entities"`` key mapping to a list of
    ``(start, end, label)`` triples.

    :param n_samples: number of training examples to generate.
    :param seed: random seed for reproducibility.
    """
    if seed is not None:
        random.seed(seed)

    data: list[tuple[str, dict[str, Any]]] = []

    for _ in range(n_samples):
        template = random.choice(_TEMPLATES)
        text = _fill_template(template)

        # Extract entities from the filled template
        entities: list[tuple[int, int, str]] = []

        # Find all entity candidates
        candidates = []
        for t in TITLES:
            candidates.append((t.title, "TITLE"))
        for o in ORG_PATTERNS:
            candidates.append((o.name, "ORG"))
        for loc in LOCATION_PATTERNS:
            candidates.append((loc.name, "LOCATION"))
        for n in _NAMES:
            candidates.append((n, "PERSON"))

        # Find spans for each candidate
        for entity_text, label in candidates:
            span = _find_entity_span(text, entity_text)
            if span is not None:
                # Check for overlap with existing entities
                overlaps = False
                for s, e, _ in entities:
                    if span[0] < e and span[1] > s:
                        overlaps = True
                        break
                if not overlaps:
                    entities.append((span[0], span[1], label))

        # Sort by start position
        entities.sort(key=lambda x: x[0])

        data.append((text, {"entities": entities}))

    return data


def export_spacy_format(
    data: list[tuple[str, dict[str, Any]]],
    output_path: str,
) -> None:
    """Export training data to a JSON file compatible with ``spacy train``.

    The output is a JSONL file with one example per line.
    """
    import json

    with open(output_path, "w", encoding="utf-8") as f:
        for text, annotations in data:
            example = {"text": text, "entities": annotations["entities"]}
            f.write(json.dumps(example, ensure_ascii=False) + "\n")


__all__ = ["generate_training_data", "export_spacy_format"]
