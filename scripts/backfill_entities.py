"""
Backfill script: populate missing entity links, aliases, and archetypes.

This script re-processes existing chapter data to:
1. Link characters to organizations via co-occurrence
2. Link characters to locations via co-occurrence
3. Detect and persist aliases
4. Optionally classify archetypes for high-frequency characters

Usage:
    python scripts/backfill_entities.py [--with-archetypes]
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.unit_of_work import UnitOfWork
from app.core.use_cases.extract_entities import ExtractEntitiesUseCase
from app.core.use_cases.ingest_entities import IngestEntitiesUseCase
from app.models import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

EXPORT_DIR = Path("data/exports")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def backfill_junction_tables() -> dict:
    """Re-process all chapters to populate junction tables."""
    stats = {
        "chapters_processed": 0,
        "char_org_links": 0,
        "char_loc_links": 0,
        "aliases_found": 0,
        "errors": 0,
    }

    uow = UnitOfWork(session_factory=SessionLocal)
    extract_uc = ExtractEntitiesUseCase()

    with uow:
        # Get all chapters
        chapters = uow.chapters.list(limit=100_000)
        total = len(chapters)
        logger.info("Processing %d chapters for backfill", total)

        for i, chapter in enumerate(chapters):
            if not chapter.content:
                continue

            try:
                # Extract entities from chapter content
                extraction = extract_uc.execute(chapter.content, chapter_id=chapter.id)

                # Use IngestEntitiesUseCase to persist with junction tables
                ingest_uc = IngestEntitiesUseCase(uow)
                result = ingest_uc.execute(extraction)

                stats["chapters_processed"] += 1
                stats["char_org_links"] += result.new_char_org_links
                stats["char_loc_links"] += result.new_char_loc_links
                stats["aliases_found"] += result.new_aliases

                if (i + 1) % 50 == 0:
                    logger.info(
                        "Progress: %d/%d chapters (%.1f%%)",
                        i + 1,
                        total,
                        (i + 1) / total * 100,
                    )
            except Exception as e:
                stats["errors"] += 1
                logger.warning("Error processing chapter %s: %s", chapter.id, e)

        uow.commit()

    logger.info("Backfill complete: %s", stats)
    return stats


def backfill_archetypes(min_frequency: int = 10) -> dict:
    """Classify archetypes for characters with frequency >= min_frequency."""
    from app.core.use_cases.classify_character_archetype import ClassifyAllCharacters
    from app.nlp.archetype_classifier import ArchetypeClassifier

    stats = {
        "characters_classified": 0,
        "errors": 0,
    }

    uow = UnitOfWork(session_factory=SessionLocal)
    classifier = ArchetypeClassifier()

    with uow:
        classify_all = ClassifyAllCharacters(
            character_repository=uow.characters,
            chapter_repository=uow.chapters,
            classifier=classifier,
        )

        # Filter to high-frequency characters only
        characters = uow.characters.list(limit=10_000)
        high_freq = [c for c in characters if (c.appearance_frequency or 0) >= min_frequency]
        logger.info(
            "Classifying archetypes for %d characters (freq >= %d)",
            len(high_freq),
            min_frequency,
        )

        for char in high_freq:
            try:
                classify_all.execute()
                stats["characters_classified"] += 1
            except Exception as e:
                stats["errors"] += 1
                logger.warning("Error classifying character %s: %s", char.id, e)

        uow.commit()

    logger.info("Archetype backfill complete: %s", stats)
    return stats


def print_data_quality_report() -> None:
    """Print a data quality report after backfill."""
    uow = UnitOfWork(session_factory=SessionLocal)

    with uow:
        characters = uow.characters.list(limit=100_000)
        organizations = uow.organizations.list(limit=100_000)
        locations = uow.locations.list(limit=100_000)

        # Count junction table entries
        char_org_count = 0
        char_loc_count = 0
        alias_count = 0
        archetype_count = 0
        for char in characters:
            char_org_count += len(char.organizations)
            char_loc_count += len(char.locations)
            alias_count += len(char.aliases)
            if char.archetype:
                archetype_count += 1

        print("\n" + "=" * 60)
        print("DATA QUALITY REPORT")
        print("=" * 60)
        print(f"Characters:           {len(characters)}")
        print(f"  - With archetype:   {archetype_count}")
        print(f"  - With aliases:     {alias_count}")
        print(f"Organizations:        {len(organizations)}")
        print(f"Locations:            {len(locations)}")
        print(f"Char-Org links:       {char_org_count}")
        print(f"Char-Loc links:       {char_loc_count}")
        print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill entity data")
    parser.add_argument(
        "--with-archetypes",
        action="store_true",
        help="Also classify archetypes (slow, requires chapter content)",
    )
    parser.add_argument(
        "--min-frequency",
        type=int,
        default=10,
        help="Minimum frequency for archetype classification (default: 10)",
    )
    args = parser.parse_args()

    start = time.time()

    # Backfill junction tables and aliases
    logger.info("Starting junction table backfill...")
    backfill_junction_tables()

    # Optionally backfill archetypes
    if args.with_archetypes:
        logger.info("Starting archetype backfill...")
        backfill_archetypes(min_frequency=args.min_frequency)

    # Print quality report
    print_data_quality_report()

    elapsed = time.time() - start
    logger.info("Total time: %.1f seconds", elapsed)


if __name__ == "__main__":
    main()
