"""
Generate embeddings in batch for all characters without embedding_vec.

Usage:
    DATABASE_URL=postgresql://murim_user:murim_password@localhost:5432/murim_db \
        python scripts/batch_embed.py [--force] [--page-size 100] [--limit N]

Options:
    --force       Regenerate embeddings even for characters that already have one
    --page-size   Characters processed per batch (default: 100)
    --limit       Stop after N characters (default: all)

Progress is logged every 500 characters. Errors per character are caught and
logged without aborting the entire batch.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch embedding generation for characters")
    parser.add_argument("--force", action="store_true", help="Regenerate existing embeddings")
    parser.add_argument("--page-size", type=int, default=100, help="Batch size (default: 100)")
    parser.add_argument("--limit", type=int, default=0, help="Max characters to process (0 = all)")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        logger.error("Set DATABASE_URL environment variable before running.")
        return 1

    # Set DATABASE_URL so app config picks it up
    os.environ["DATABASE_URL"] = database_url

    from app.core.unit_of_work import UnitOfWork
    from app.core.use_cases.generate_embeddings import GenerateEmbeddingsUseCase
    from app.models.base import SessionLocal

    logger.info("Loading sentence-transformers encoder...")
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        encoder = model.encode
        logger.info("Encoder ready.")
    except Exception as exc:
        logger.error("Failed to load encoder: %s", exc)
        return 1

    # Count characters to process
    with SessionLocal() as session:
        from sqlalchemy import text

        if args.force:
            total_q = session.execute(text("SELECT COUNT(*) FROM characters")).scalar()
        else:
            total_q = session.execute(
                text("SELECT COUNT(*) FROM characters WHERE embedding_vec IS NULL")
            ).scalar()

    total = min(total_q, args.limit) if args.limit else total_q
    logger.info(
        "Characters to embed: %d (force=%s, limit=%s)",
        total,
        args.force,
        args.limit or "none",
    )

    if total == 0:
        logger.info("Nothing to do — all characters already have embeddings.")
        return 0

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

        with SessionLocal() as session:
            from sqlalchemy import text as sa_text

            if args.force:
                rows = session.execute(
                    sa_text(
                        "SELECT id FROM characters ORDER BY canonical_name "
                        "LIMIT :limit OFFSET :offset"
                    ),
                    {"limit": page_size, "offset": offset},
                ).fetchall()
            else:
                rows = session.execute(
                    sa_text(
                        "SELECT id FROM characters WHERE embedding_vec IS NULL "
                        "ORDER BY canonical_name LIMIT :limit OFFSET :offset"
                    ),
                    {"limit": page_size, "offset": offset},
                ).fetchall()

        if not rows:
            break

        character_ids = [str(row[0]) for row in rows]

        for char_id in character_ids:
            try:
                with SessionLocal() as session:
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
                    # Use GenerateEmbeddingsUseCase directly
                    uc = GenerateEmbeddingsUseCase(uow, encoder=encoder)
                    result = uc.execute(char_id)
                    if result.success:
                        success += 1
                    else:
                        logger.warning("Failed to embed %s: %s", char_id, result.error)
                        failures += 1
            except Exception as exc:
                logger.warning("Error embedding character %s: %s", char_id, exc)
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
            offset = 0  # When filtering by IS NULL, offset doesn't advance (rows disappear)

    elapsed = time.time() - start_time
    logger.info(
        "\n── Batch embedding complete ─────────────────────────\n"
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

    return 0 if failures == 0 or success / (success + failures) >= 0.95 else 1


if __name__ == "__main__":
    sys.exit(main())
