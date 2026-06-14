"""
Classify archetypes in batch for all characters without archetype.

Usage:
    DATABASE_URL=postgresql://murim_user:murim_password@localhost:5432/murim_db \
        python scripts/batch_classify.py [--force] [--page-size 100] [--limit N] [--report]

Options:
    --force       Reclassify even characters that already have an archetype
    --page-size   Characters processed per batch (default: 100)
    --limit       Stop after N characters (default: all)
    --report      After classification, print distribution statistics

Progress is logged every 500 characters. Errors per character are caught and
logged without aborting the entire batch.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import Counter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def print_distribution_report(database_url: str) -> None:
    """Query DB and print archetype distribution statistics."""
    from sqlalchemy import create_engine, text

    engine = create_engine(database_url)
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT archetype FROM characters WHERE archetype IS NOT NULL")
        ).fetchall()

    role_counter: Counter[str] = Counter()
    combat_counter: Counter[str] = Counter()
    trait_counter: Counter[str] = Counter()
    role_confidences: list[float] = []
    combat_confidences: list[float] = []

    for (archetype_json,) in rows:
        try:
            data = json.loads(archetype_json)
            role_counter[data.get("narrative_role", "unknown")] += 1
            combat_counter[data.get("combat_style", "unknown")] += 1
            for trait in data.get("personality_traits", []):
                trait_counter[trait] += 1
            role_confidences.append(float(data.get("role_confidence", 0.0)))
            combat_confidences.append(float(data.get("combat_confidence", 0.0)))
        except Exception:
            pass

    total = len(rows)
    logger.info("\n═══════════════════════════════════════════════════════")
    logger.info("  ARCHETYPE DISTRIBUTION REPORT  (%d characters classified)", total)
    logger.info("═══════════════════════════════════════════════════════")

    logger.info("\n── NarrativeRole ────────────────────────────────────")
    for role, count in role_counter.most_common():
        bar = "█" * int(40 * count / total)
        logger.info("  %-25s %5d  %5.1f%%  %s", role, count, 100 * count / total, bar)

    logger.info("\n── CombatStyle ──────────────────────────────────────")
    for style, count in combat_counter.most_common():
        bar = "█" * int(40 * count / total)
        logger.info("  %-25s %5d  %5.1f%%  %s", style, count, 100 * count / total, bar)

    logger.info("\n── PersonalityTrait (top 15) ────────────────────────")
    for trait, count in trait_counter.most_common(15):
        bar = "█" * int(40 * count / total)
        logger.info("  %-25s %5d  %5.1f%%  %s", trait, count, 100 * count / total, bar)

    if role_confidences:
        avg_role = sum(role_confidences) / len(role_confidences)
        avg_combat = sum(combat_confidences) / len(combat_confidences)
        logger.info("\n── Confidence Scores ────────────────────────────────")
        logger.info("  Average role_confidence    %.3f", avg_role)
        logger.info("  Average combat_confidence  %.3f", avg_combat)

    engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch archetype classification for characters")
    parser.add_argument("--force", action="store_true", help="Reclassify existing archetypes")
    parser.add_argument("--page-size", type=int, default=100, help="Batch size (default: 100)")
    parser.add_argument("--limit", type=int, default=0, help="Max characters to process (0 = all)")
    parser.add_argument("--report", action="store_true", help="Print distribution report after run")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        logger.error("Set DATABASE_URL environment variable before running.")
        return 1

    os.environ["DATABASE_URL"] = database_url

    from sqlalchemy import create_engine, text

    engine = create_engine(database_url)
    with engine.connect() as conn:
        if args.force:
            total_q = conn.execute(text("SELECT COUNT(*) FROM characters")).scalar()
        else:
            total_q = conn.execute(
                text("SELECT COUNT(*) FROM characters WHERE archetype IS NULL")
            ).scalar()
    engine.dispose()

    total = min(total_q, args.limit) if args.limit else total_q
    logger.info(
        "Characters to classify: %d (force=%s, limit=%s)",
        total,
        args.force,
        args.limit or "none",
    )

    if total == 0:
        logger.info("Nothing to do — all characters already have archetypes.")
        if args.report:
            print_distribution_report(database_url)
        return 0

    from app.core.use_cases.classify_character_archetype import ClassifyCharacterArchetype
    from app.models.base import SessionLocal
    from app.nlp.archetype_classifier import ArchetypeClassifier

    classifier = ArchetypeClassifier()
    processed = 0
    success = 0
    failures = 0
    start_time = time.time()

    offset = 0
    while True:
        if args.limit and processed >= args.limit:
            break

        page_size = args.page_size
        if args.limit and processed + page_size > args.limit:
            page_size = args.limit - processed

        engine_q = create_engine(database_url)
        with engine_q.connect() as conn:
            if args.force:
                rows = conn.execute(
                    text(
                        "SELECT id FROM characters ORDER BY canonical_name "
                        "LIMIT :limit OFFSET :offset"
                    ),
                    {"limit": page_size, "offset": offset},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        "SELECT id FROM characters WHERE archetype IS NULL "
                        "ORDER BY canonical_name LIMIT :limit OFFSET :offset"
                    ),
                    {"limit": page_size, "offset": offset},
                ).fetchall()
        engine_q.dispose()

        if not rows:
            break

        character_ids = [str(row[0]) for row in rows]

        for char_id in character_ids:
            try:
                with SessionLocal() as session:
                    from app.core.unit_of_work import UnitOfWork
                    from app.repositories.chapter_repository import ChapterRepository
                    from app.repositories.character_repository import CharacterRepository
                    from app.repositories.location_repository import LocationRepository
                    from app.repositories.novel_repository import NovelRepository
                    from app.repositories.organization_repository import OrganizationRepository

                    uow = UnitOfWork(
                        session_factory=lambda s=session: s,
                        character_repo_class=CharacterRepository,
                        chapter_repo_class=ChapterRepository,
                        novel_repo_class=NovelRepository,
                        location_repo_class=LocationRepository,
                        organization_repo_class=OrganizationRepository,
                    )
                    uc = ClassifyCharacterArchetype(
                        character_repository=uow.characters,
                        chapter_repository=uow.chapters,
                        classifier=classifier,
                    )
                    uc.execute(char_id)
                    success += 1
            except Exception as exc:
                logger.warning("Error classifying character %s: %s", char_id, exc)
                failures += 1

            processed += 1
            if processed % 500 == 0 or processed == total:
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                eta = (total - processed) / rate if rate > 0 else 0
                logger.info(
                    "Progress: %d/%d (%.0f%%) | ✅ %d | ❌ %d | %.1f char/s | ETA %.0fs",
                    processed,
                    total,
                    100 * processed / total,
                    success,
                    failures,
                    rate,
                    eta,
                )

        offset += page_size
        if not args.force:
            offset = 0  # Rows disappear from IS NULL filter as they're classified

    elapsed = time.time() - start_time
    logger.info(
        "\n── Batch classification complete ────────────────────\n"
        "  Total processed : %d\n"
        "  Success         : %d (%.1f%%)\n"
        "  Failures        : %d (%.1f%%)\n"
        "  Time elapsed    : %.0fs\n"
        "  Average rate    : %.1f char/s",
        processed,
        success,
        100 * success / processed if processed else 0,
        failures,
        100 * failures / processed if processed else 0,
        elapsed,
        processed / elapsed if elapsed > 0 else 0,
    )

    if args.report:
        print_distribution_report(database_url)

    return 0 if failures == 0 or success / (success + failures) >= 0.95 else 1


if __name__ == "__main__":
    sys.exit(main())
