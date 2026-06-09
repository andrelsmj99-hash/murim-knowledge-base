#!/usr/bin/env python3
"""
Batch ingestion pipeline for multiple Murim novels.

Reads config/novels_to_ingest.yaml and processes pending novels sequentially.
Supports resume (skips already-ingested chapters) and dry-run mode.

Usage:
    python scripts/batch_ingest.py                     # Process all pending novels
    python scripts/batch_ingest.py --novel <slug>      # Process one novel
    python scripts/batch_ingest.py --dry-run           # Test without persisting
    python scripts/batch_ingest.py --list              # Show novel statuses
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.unit_of_work import UnitOfWork
from app.core.use_cases.classify_character_archetype import ClassifyAllCharacters
from app.core.use_cases.deduplicate_characters import DeduplicateCharactersUseCase
from app.core.use_cases.extract_entities import ExtractEntitiesUseCase
from app.core.use_cases.ingest_chapter import IngestChapterUseCase
from app.core.use_cases.ingest_entities import IngestEntitiesUseCase
from app.nlp.archetype_classifier import ArchetypeClassifier
from app.scrapers.novelfire import NovelFireScraper

CONFIG_PATH = Path("config/novels_to_ingest.yaml")
LOG_DIR = Path("logs")
EXPORT_DIR = Path("data/exports")
PROGRESS_DIR = Path("data/progress")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("batch_ingest")


def load_config() -> dict[str, Any]:
    """Load novels config from YAML file."""
    if not CONFIG_PATH.exists():
        logger.error("Config file not found: %s", CONFIG_PATH)
        sys.exit(1)
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(config: dict[str, Any]) -> None:
    """Save updated config back to YAML file."""
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    logger.info("Config updated: %s", CONFIG_PATH)


def get_novel_config(config: dict[str, Any], slug: str) -> dict[str, Any] | None:
    """Find a novel config entry by slug."""
    for novel in config.get("novels", []):
        if novel.get("slug") == slug:
            return novel
    return None


def scrape_chapters(scraper: NovelFireScraper, limit: int | None = None) -> list[dict]:
    """Scrape chapter list and optionally limit count."""
    logger.info("Fetching chapter list for %s...", scraper.novel_slug)
    chapters = scraper.get_chapter_list()
    if limit:
        chapters = chapters[:limit]
    logger.info("Will process %d chapters", len(chapters))
    return chapters


def ingest_chapters(
    scraper: NovelFireScraper,
    chapters: list[dict],
    uow: UnitOfWork,
    resume: bool = True,
) -> list[tuple[dict, Any]]:
    """Ingest chapters into DB, returning list of (chapter_info, IngestResult) tuples."""
    ingest_uc = IngestChapterUseCase(uow)
    meta = scraper.get_novel_metadata()
    logger.info("Novel metadata: %s", meta.get("title"))

    results: list[tuple[dict, Any]] = []
    for i, ch_info in enumerate(chapters):
        number = ch_info["chapter_number"]

        # Check DB for existing chapters (resume support)
        if resume:
            novel = uow.novels.get_by_title_author(meta["title"], meta.get("author"))
            if novel and uow.novels.chapter_exists(novel.id, number):
                logger.debug("Chapter %d already in DB, skipping fetch", number)
                continue

        try:
            chapter_data = scraper.get_chapter_content(ch_info)
        except Exception as exc:
            logger.error("Failed to scrape chapter %d: %s", number, exc)
            continue

        if not chapter_data:
            logger.warning("Empty content for chapter %d", number)
            continue

        try:
            result = ingest_uc.execute(meta, chapter_data)
            results.append((ch_info, result))
            logger.info(
                "Chapter %d/%d ingested: %s (skipped=%s)",
                i + 1,
                len(chapters),
                result.chapter_number,
                result.skipped,
            )
        except Exception as exc:
            logger.error("Failed to ingest chapter %d: %s", number, exc)
            continue

    return results


def _is_false_positive_name(name: str) -> bool:
    """Check if a name is a likely NER false positive."""
    import re

    # Reject names with newlines, tabs, or excessive whitespace
    if re.search(r"[\n\r\t]", name):
        return True
    # Reject single-character names (except common Chinese char patterns)
    if len(name.strip()) <= 1:
        return True
    # Reject names that are common onomatopoeia or English words
    false_positives = {
        "pak",
        "thud",
        "swish",
        "flinch",
        "swoosh",
        "clench",
        "boom",
        "grab",
        "reven",
        "mur",
        "seeing",
        "struggle",
        "everything",
        "inside",
        "although",
        "ah",
        "oh",
        "um",
        "eh",
        "hmm",
        "shh",
        "psst",
    }
    return name.lower().strip() in false_positives


def extract_and_ingest_entities(
    chapter_results: list[tuple[dict, Any]],
) -> dict:
    """Run NLP extraction on all ingested chapters and persist entities.

    Uses a fresh UnitOfWork per chapter to prevent cascading rollbacks from
    UNIQUE constraint violations on badly-formatted NER names.
    """
    extract_uc = ExtractEntitiesUseCase()

    stats: dict[str, int] = {
        "chapters_processed": 0,
        "total_characters": 0,
        "total_organizations": 0,
        "total_locations": 0,
        "total_relationships": 0,
    }

    for _ch_info, ingest_result in chapter_results:
        chapter_id = ingest_result.chapter_id

        try:
            with UnitOfWork() as uow:
                chapter = uow.chapters.get(chapter_id) if hasattr(uow.chapters, "get") else None
                if not chapter:
                    logger.warning("Could not fetch chapter %s from DB, skipping", chapter_id)
                    continue

                content = chapter.content if hasattr(chapter, "content") else ""
                if not content:
                    continue

                extraction = extract_uc.execute(content, chapter_id=chapter_id)
                # Filter out false positive characters before ingestion
                extraction.characters = [
                    ch for ch in extraction.characters if not _is_false_positive_name(ch.name)
                ]
                ingest_entities_uc = IngestEntitiesUseCase(uow)
                entities_result = ingest_entities_uc.execute(
                    extraction, novel_id=ingest_result.novel_id
                )

                stats["chapters_processed"] += 1
                stats["total_characters"] += (
                    entities_result.new_characters + entities_result.updated_characters
                )
                stats["total_organizations"] += entities_result.new_organizations
                stats["total_locations"] += entities_result.new_locations
                stats["total_relationships"] += entities_result.new_relationships

                logger.info(
                    "Chapter %d: +%d chars, +%d orgs, +%d locs, +%d rels",
                    ingest_result.chapter_number,
                    entities_result.new_characters,
                    entities_result.new_organizations,
                    entities_result.new_locations,
                    entities_result.new_relationships,
                )
        except Exception as exc:
            logger.error("Entity extraction failed for chapter %s: %s", chapter_id, exc)

    return stats


def deduplicate_all_characters(uow: UnitOfWork) -> dict:
    """Run global character deduplication."""
    dedup_uc = DeduplicateCharactersUseCase()

    all_chars: list = []
    offset = 0
    while True:
        batch = uow.characters.list(limit=1000, offset=offset)
        if not batch:
            break
        all_chars.extend(batch)
        offset += len(batch)

    if not all_chars:
        logger.warning("No characters found for deduplication")
        return {"before": 0, "after": 0, "merged": 0}

    before = len(all_chars)
    result = dedup_uc.execute(all_chars)
    after = len(result.canonical_characters)
    merged = before - after

    logger.info("Deduplication: %d -> %d characters (%d merged)", before, after, merged)
    return {"before": before, "after": after, "merged": merged}


def classify_all_archetypes(uow: UnitOfWork) -> dict:
    """Classify archetypes for all characters in the database."""
    classifier = ArchetypeClassifier()
    classify_uc = ClassifyAllCharacters(
        character_repository=uow.characters,
        chapter_repository=uow.chapters,
        classifier=classifier,
    )

    results = classify_uc.execute()
    logger.info("Classified %d character archetypes", len(results))

    from collections import Counter

    role_counts = Counter(arch.narrative_role.value for _, arch in results)
    combat_counts = Counter(arch.combat_style.value for _, arch in results)

    logger.info("Narrative roles: %s", dict(role_counts))
    logger.info("Combat styles: %s", dict(combat_counts))

    return {
        "characters_classified": len(results),
        "narrative_roles": dict(role_counts),
        "combat_styles": dict(combat_counts),
    }


def process_novel(
    novel_cfg: dict[str, Any],
    *,
    dry_run: bool = False,
    max_chapters: int | None = None,
    scrape_only: bool = False,
) -> dict[str, Any]:
    """Full pipeline for a single novel. Returns summary dict."""
    slug = novel_cfg["slug"]
    source = novel_cfg.get("source", "novelfire")
    title = novel_cfg.get("title", slug)
    logger.info("=" * 60)
    logger.info("Processing: %s (%s)", title, slug)
    logger.info("=" * 60)

    start_time = time.time()
    summary: dict[str, Any] = {
        "slug": slug,
        "title": title,
        "status": "pending",
        "dry_run": dry_run,
    }

    if source != "novelfire":
        logger.error("Only novelfire source supported currently, got '%s'", source)
        summary["status"] = "error"
        summary["error"] = f"Unsupported source: {source}"
        return summary

    chapter_list_pages = novel_cfg.get("chapter_list_pages", 5)

    if dry_run:
        logger.info("DRY RUN — testing scraper without persisting")
        scraper = NovelFireScraper(slug, chapter_list_pages=chapter_list_pages)
        try:
            meta = scraper.get_novel_metadata()
            summary["metadata"] = meta
            logger.info("Metadata OK: %s by %s", meta.get("title"), meta.get("author"))

            chapters = scrape_chapters(scraper, limit=max_chapters or 5)
            summary["chapters_found"] = len(chapters)

            if chapters:
                ch_data = scraper.get_chapter_content(chapters[0])
                if ch_data:
                    summary["sample_chapter_words"] = ch_data.get("word_count", 0)
                    logger.info("Sample chapter OK: %d words", ch_data.get("word_count", 0))
                else:
                    summary["status"] = "error"
                    summary["error"] = "Failed to scrape sample chapter"
        except Exception as exc:
            logger.error("Dry run failed: %s", exc)
            summary["status"] = "error"
            summary["error"] = str(exc)
        else:
            summary["status"] = "dry_run_ok"
        summary["elapsed_seconds"] = round(time.time() - start_time, 2)
        return summary

    # Phase 1: Scrape
    logger.info("Phase 1: Scraping chapters...")
    scraper = NovelFireScraper(slug, chapter_list_pages=chapter_list_pages)
    chapters = scrape_chapters(scraper, limit=max_chapters)

    if not chapters:
        logger.warning("No chapters found for %s", slug)
        summary["status"] = "no_chapters"
        summary["elapsed_seconds"] = round(time.time() - start_time, 2)
        return summary

    summary["chapters_found"] = len(chapters)

    # Phase 2: Ingest chapters
    logger.info("Phase 2: Ingesting chapters into database...")
    with UnitOfWork() as uow:
        chapter_results = ingest_chapters(scraper, chapters, uow, resume=True)
        logger.info("Ingested %d chapters", len(chapter_results))
    summary["chapters_ingested"] = len(chapter_results)

    if scrape_only:
        logger.info("Scrape-only mode, skipping NLP")
        summary["entity_extraction"] = {"skipped": True}
        summary["deduplication"] = {"skipped": True}
        summary["archetype_classification"] = {"skipped": True}
        summary["status"] = "scraped"
        summary["elapsed_seconds"] = round(time.time() - start_time, 2)
        return summary

    # Phase 3: NLP extraction
    if chapter_results:
        logger.info("Phase 3: Extracting entities with NLP...")
        with UnitOfWork() as uow:
            entity_stats = extract_and_ingest_entities(chapter_results)
            summary["entity_extraction"] = entity_stats
            logger.info("Entity extraction stats: %s", entity_stats)

        # Phase 4: Deduplication
        logger.info("Phase 4: Deduplicating characters...")
        with UnitOfWork() as uow:
            dedup_stats = deduplicate_all_characters(uow)
            summary["deduplication"] = dedup_stats
            logger.info("Deduplication stats: %s", dedup_stats)
    else:
        summary["entity_extraction"] = {"skipped": True}
        summary["deduplication"] = {"skipped": True}

    # Phase 5: Archetype Classification
    logger.info("Phase 5: Classifying character archetypes...")
    with UnitOfWork() as uow:
        archetype_stats = classify_all_archetypes(uow)
        summary["archetype_classification"] = archetype_stats
        logger.info("Archetype classification stats: %s", archetype_stats)

    summary["status"] = "complete"
    summary["elapsed_seconds"] = round(time.time() - start_time, 2)
    return summary


def update_config_status(
    config: dict[str, Any],
    slug: str,
    status: str,
    chapters_ingested: int | None = None,
) -> None:
    """Update a novel's status in the YAML config."""
    for novel in config.get("novels", []):
        if novel.get("slug") == slug:
            novel["status"] = status
            if chapters_ingested is not None:
                novel["chapters_ingested"] = chapters_ingested
            novel["last_processed"] = str(datetime.now(UTC).date())
            break
    save_config(config)


def list_novel_statuses(config: dict[str, Any]) -> None:
    """Print a summary table of all novels and their statuses."""
    print(f"\n{'Title':<45} {'Slug':<35} {'Status':<12} {'Chapters':<10}")
    print("-" * 102)
    for novel in config.get("novels", []):
        print(
            f"{novel.get('title', '?'):<45} "
            f"{novel.get('slug', '?'):<35} "
            f"{novel.get('status', '?'):<12} "
            f"{novel.get('chapters_ingested', 0):<10}"
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch ingestion for Murim novels")
    parser.add_argument(
        "--novel",
        type=str,
        default=None,
        help="Process a single novel by slug (e.g. 'rebirth-of-the-heavenly-demon')",
    )
    parser.add_argument("--dry-run", action="store_true", help="Test scraper without persisting")
    parser.add_argument(
        "--list", action="store_true", dest="list_status", help="List novel statuses"
    )
    parser.add_argument("--scrape-only", action="store_true", help="Only scrape, skip NLP")
    parser.add_argument("--limit", type=int, default=None, help="Limit chapters per novel")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Set up file logging
    file_handler = logging.FileHandler(
        LOG_DIR / f"batch_ingest_{datetime.now(UTC).date().strftime('%Y%m%d')}.log",
        mode="a",
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logging.getLogger().addHandler(file_handler)

    config = load_config()

    if args.list_status:
        list_novel_statuses(config)
        return

    if args.novel:
        novel_cfg = get_novel_config(config, args.novel)
        if not novel_cfg:
            logger.error("Novel '%s' not found in config", args.novel)
            sys.exit(1)
        novels_to_process = [novel_cfg]
    else:
        novels_to_process = [n for n in config.get("novels", []) if n.get("status") == "pending"]

    if not novels_to_process:
        logger.info("No pending novels to process")
        return

    logger.info("Processing %d novel(s)", len(novels_to_process))

    results: list[dict[str, Any]] = []
    for novel_cfg in novels_to_process:
        slug = novel_cfg["slug"]
        result = process_novel(
            novel_cfg,
            dry_run=args.dry_run,
            max_chapters=args.limit,
            scrape_only=args.scrape_only,
        )
        results.append(result)

        # Update config after each novel
        if result.get("status") == "complete":
            chapters_ingested = result.get("chapters_ingested", 0)
            update_config_status(config, slug, "complete", chapters_ingested)
        elif result.get("status") == "scraped":
            chapters_ingested = result.get("chapters_ingested", 0)
            update_config_status(config, slug, "scraped", chapters_ingested)
        elif result.get("status") == "dry_run_ok":
            update_config_status(config, slug, "pending")  # keep pending after dry-run

    # Write summary
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = (
        EXPORT_DIR / f"batch_ingest_summary_{datetime.now(UTC).date().strftime('%Y%m%d')}.json"
    )
    summary_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    logger.info("Summary written to %s", summary_path)

    # Print final summary
    logger.info("=" * 60)
    logger.info("BATCH INGESTION COMPLETE")
    for r in results:
        status = r.get("status", "?")
        elapsed = r.get("elapsed_seconds", 0)
        title = r.get("title", r.get("slug", "?"))
        ingested = r.get("chapters_ingested", 0)
        logger.info("  %s: %s (%d chapters, %.1fs)", title, status, ingested, elapsed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
