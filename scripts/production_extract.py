#!/usr/bin/env python3
"""
Production extraction script for Nano Machine (novelfire.net).

Generic extraction pipeline:
1. Scrape chapter list (paginated)
2. Ingest chapters into SQLite
3. Extract NLP entities per chapter
4. Ingest entities into DB
5. Deduplicate characters
6. Build knowledge graph
7. Export to JSON/CSV

Usage:
    python scripts/production_extract.py [--resume] [--limit N] [--skip-nlp]
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.base import SessionLocal
from app.core.unit_of_work import UnitOfWork
from app.core.use_cases.ingest_chapter import IngestChapterUseCase
from app.core.use_cases.extract_entities import ExtractEntitiesUseCase
from app.core.use_cases.ingest_entities import IngestEntitiesUseCase
from app.core.use_cases.deduplicate_characters import DeduplicateCharactersUseCase
from app.scrapers.novelfire import NovelFireScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/extraction.log", mode="a"),
    ],
)
logger = logging.getLogger("production_extract")

NOVEL_SLUG = "nano-machine"
EXPORT_DIR = Path("data/exports")
PROGRESS_DIR = Path("data/progress")


def scrape_chapters(scraper: NovelFireScraper, limit: int | None = None) -> list[dict]:
    """Scrape chapter list and optionally limit count."""
    logger.info("Fetching chapter list for %s...", NOVEL_SLUG)
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
) -> list[dict]:
    """Ingest chapters into DB, returning list of (chapter_info, IngestResult) tuples."""
    ingest_uc = IngestChapterUseCase(uow)
    meta = scraper.get_novel_metadata()
    logger.info("Novel metadata: %s", meta.get("title"))

    results = []
    for i, ch_info in enumerate(chapters):
        number = ch_info["chapter_number"]
        # Check if already ingested (resume support)
        if resume:
            existing = uow.novels.chapter_exists_by_number(
                meta.get("title", ""), number
            ) if hasattr(uow.novels, 'chapter_exists_by_number') else None
            # Fallback: try loading progress file
            progress_file = PROGRESS_DIR / f"progress_novelfire_{NOVEL_SLUG}.json"
            if progress_file.exists():
                progress = json.loads(progress_file.read_text())
                if number in progress.get("processed_chapters", []):
                    logger.debug("Chapter %d already processed, skipping fetch", number)
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


def extract_and_ingest_entities(
    uow: UnitOfWork,
    chapter_results: list[tuple[dict, Any]],
) -> dict:
    """Run NLP extraction on all ingested chapters and persist entities.

    chapter_results is a list of (chapter_info, IngestResult) tuples.
    We need to re-fetch the chapter content from the DB since the scraper
    payloads are not retained.
    """
    extract_uc = ExtractEntitiesUseCase()
    ingest_entities_uc = IngestEntitiesUseCase(uow)

    stats = {
        "chapters_processed": 0,
        "total_characters": 0,
        "total_organizations": 0,
        "total_locations": 0,
        "total_relationships": 0,
    }

    for ch_info, ingest_result in chapter_results:
        chapter_id = ingest_result.chapter_id
        # Fetch chapter content from DB
        chapter = uow.chapters.get(chapter_id) if hasattr(uow.chapters, 'get') else None
        if not chapter:
            logger.warning("Could not fetch chapter %s from DB, skipping", chapter_id)
            continue

        content = chapter.content if hasattr(chapter, 'content') else ""
        if not content:
            continue

        try:
            extraction = extract_uc.execute(content, chapter_id=chapter_id)
            entities_result = ingest_entities_uc.execute(extraction)

            stats["chapters_processed"] += 1
            stats["total_characters"] += entities_result.new_characters + entities_result.updated_characters
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

    # Load all characters (paginate if needed)
    all_chars = []
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


def export_data(uow: UnitOfWork) -> dict:
    """Export all data to JSON and CSV files."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Export characters (paginate)
    chars_data = []
    offset = 0
    while True:
        batch = uow.characters.list(limit=1000, offset=offset)
        if not batch:
            break
        for c in batch:
            chars_data.append({
                "id": c.id,
                "name": c.name,
                "canonical_name": c.canonical_name,
                "gender": c.gender,
                "description": c.description,
                "titles": c.titles,
                "aliases": [a.value for a in c.aliases] if hasattr(c, 'aliases') else [],
                "appearance_frequency": c.appearance_frequency,
            })
        offset += len(batch)

    # Export organizations (paginate)
    orgs_data = []
    offset = 0
    while True:
        batch = uow.organizations.list(limit=1000, offset=offset)
        if not batch:
            break
        for o in batch:
            orgs_data.append({
                "id": o.id,
                "name": o.name,
                "type": o.type,
            })
        offset += len(batch)

    # Export locations (paginate)
    locs_data = []
    offset = 0
    while True:
        batch = uow.locations.list(limit=1000, offset=offset)
        if not batch:
            break
        for l in batch:
            locs_data.append({
                "id": l.id,
                "name": l.name,
                "type": l.type,
            })
        offset += len(batch)

    # Write JSON
    (EXPORT_DIR / "characters.json").write_text(json.dumps(chars_data, indent=2, ensure_ascii=False))
    (EXPORT_DIR / "organizations.json").write_text(json.dumps(orgs_data, indent=2, ensure_ascii=False))
    (EXPORT_DIR / "locations.json").write_text(json.dumps(locs_data, indent=2, ensure_ascii=False))

    # Write CSV
    if chars_data:
        with open(EXPORT_DIR / "characters.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=chars_data[0].keys())
            writer.writeheader()
            writer.writerows(chars_data)

    if orgs_data:
        with open(EXPORT_DIR / "organizations.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=orgs_data[0].keys())
            writer.writeheader()
            writer.writerows(orgs_data)

    if locs_data:
        with open(EXPORT_DIR / "locations.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=locs_data[0].keys())
            writer.writeheader()
            writer.writerows(locs_data)

    stats = {
        "characters": len(chars_data),
        "organizations": len(orgs_data),
        "locations": len(locs_data),
        "export_dir": str(EXPORT_DIR),
    }
    logger.info("Exported data to %s", EXPORT_DIR)
    return stats


def main():
    parser = argparse.ArgumentParser(description="Production extraction for Nano Machine")
    parser.add_argument("--resume", action="store_true", default=True, help="Resume from checkpoint")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of chapters to process")
    parser.add_argument("--skip-nlp", action="store_true", help="Skip NLP entity extraction")
    parser.add_argument("--scrape-only", action="store_true", help="Only scrape chapters, skip NLP")
    parser.add_argument("--nlp-only", action="store_true", help="Only run NLP on already scraped chapters")
    args = parser.parse_args()

    start_time = time.time()
    logger.info("=" * 60)
    logger.info("Starting Nano Machine extraction")
    logger.info("=" * 60)

    if args.nlp_only:
        # Only run NLP on existing chapters
        logger.info("Running NLP extraction only...")
        with UnitOfWork() as uow:
            # Get all chapters
            from sqlalchemy import text
            result = uow.session.execute(text("SELECT id, novel_id, chapter_number FROM chapters ORDER BY chapter_number"))
            chapters = result.fetchall()
            logger.info("Found %d chapters in DB", len(chapters))

            # Create chapter_results format expected by extract_and_ingest_entities
            chapter_results = []
            for ch in chapters:
                chapter_id = str(ch[0])
                # Create a mock ingest_result-like object
                class MockResult:
                    def __init__(self, chapter_id, chapter_number):
                        self.chapter_id = chapter_id
                        self.chapter_number = chapter_number
                        self.skipped = True
                chapter_results.append(({}, MockResult(chapter_id, ch[2])))

            entity_stats = extract_and_ingest_entities(uow, chapter_results)
            logger.info("Entity extraction stats: %s", entity_stats)

            # Dedup
            dedup_stats = deduplicate_all_characters(uow)
            logger.info("Deduplication stats: %s", dedup_stats)

            # Export
            export_stats = export_data(uow)
    else:
        # Phase 1: Scrape
        scraper = NovelFireScraper(NOVEL_SLUG, chapter_list_pages=5)
        chapters = scrape_chapters(scraper, limit=args.limit)

        # Phase 2: Ingest chapters
        logger.info("Phase 2: Ingesting chapters into database...")
        with UnitOfWork() as uow:
            chapter_results = ingest_chapters(scraper, chapters, uow, resume=args.resume)
            logger.info("Ingested %d chapters", len(chapter_results))

        if args.scrape_only:
            logger.info("Scrape-only mode, skipping NLP")
            entity_stats = {"skipped": True}
            dedup_stats = {"skipped": True}
            export_stats = {}
        elif not args.skip_nlp and chapter_results:
            # Phase 3: NLP extraction
            logger.info("Phase 3: Extracting entities with NLP...")
            with UnitOfWork() as uow:
                entity_stats = extract_and_ingest_entities(uow, chapter_results)
                logger.info("Entity extraction stats: %s", entity_stats)

            # Phase 4: Deduplication
            logger.info("Phase 4: Deduplicating characters...")
            with UnitOfWork() as uow:
                dedup_stats = deduplicate_all_characters(uow)
                logger.info("Deduplication stats: %s", dedup_stats)
        else:
            entity_stats = {"skipped": True}
            dedup_stats = {"skipped": True}

        # Phase 5: Export
        logger.info("Phase 5: Exporting data...")
        with UnitOfWork() as uow:
            export_stats = export_data(uow)

    elapsed = time.time() - start_time
    summary = {
        "chapters_scraped": len(chapters) if not args.nlp_only else 0,
        "chapters_ingested": len(chapter_results) if not args.nlp_only else 0,
        "entity_extraction": entity_stats,
        "deduplication": dedup_stats,
        "export": export_stats,
        "elapsed_seconds": round(elapsed, 2),
    }

    # Write summary
    (EXPORT_DIR / "extraction_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False)
    )

    logger.info("=" * 60)
    logger.info("Extraction complete!")
    logger.info("Summary: %s", json.dumps(summary, indent=2))
    logger.info("=" * 60)

    return summary


if __name__ == "__main__":
    main()
