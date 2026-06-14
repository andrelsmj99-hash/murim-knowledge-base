"""
Migrate data from murim_dev.db (SQLite) to PostgreSQL.

Usage:
    DATABASE_URL=postgresql://murim_user:murim_password@localhost:5432/murim_db \
        python scripts/migrate_sqlite_to_postgres.py [--source murim_dev.db] [--dry-run]

Requirements:
    - Source SQLite file exists (default: murim_dev.db in project root)
    - Target Postgres is running with schema already applied (alembic upgrade head)
    - Python venv activated with all dependencies installed

Migration order respects foreign key constraints:
    novels → chapters → locations → organizations → characters →
    aliases → titles → relationships →
    character_locations → character_organizations → organization_relationships
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Migration order (respects FK dependencies) ────────────────────────────────

MIGRATION_ORDER = [
    "novels",
    "chapters",
    "locations",
    "organizations",
    "characters",
    "aliases",
    "titles",
    "relationships",
    "character_locations",
    "character_organizations",
    "organization_relationships",
]


def get_sqlite_counts(sqlite_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(str(sqlite_path))
    try:
        counts: dict[str, int] = {}
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row[0] for row in cursor.fetchall() if row[0] != "alembic_version"]
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
            counts[table] = cursor.fetchone()[0]
        return counts
    finally:
        conn.close()


def migrate_table(
    table: str,
    sqlite_conn: sqlite3.Connection,
    pg_engine: sa.Engine,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Migrate one table. Returns (migrated, skipped) counts."""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"SELECT * FROM {table}")  # noqa: S608
    rows = cursor.fetchall()
    col_names = [d[0] for d in cursor.description]

    if not rows:
        return 0, 0

    migrated = 0
    skipped = 0

    if dry_run:
        logger.info("[DRY-RUN] %s: would migrate %d rows", table, len(rows))
        return len(rows), 0

    with pg_engine.begin() as pg_conn:
        # Determine primary key column(s) for conflict detection
        pk_col = _get_pk_column(table)

        for row in rows:
            record = dict(zip(col_names, row, strict=False))
            # Handle NULL embedding_vec (leave as NULL — will be populated by batch_embed.py)
            if "embedding_vec" in record and record["embedding_vec"] is None:
                record["embedding_vec"] = None

            if pk_col:
                # Check if record already exists
                exists = pg_conn.execute(
                    text(f"SELECT 1 FROM {table} WHERE {pk_col} = :pk"),  # noqa: S608
                    {"pk": record[pk_col]},
                ).fetchone()
                if exists:
                    skipped += 1
                    continue

            cols = ", ".join(record.keys())
            placeholders = ", ".join(f":{k}" for k in record)
            pg_conn.execute(
                text(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"),  # noqa: S608
                record,
            )
            migrated += 1

    return migrated, skipped


def _get_pk_column(table: str) -> str | None:
    pk_map = {
        "novels": "id",
        "chapters": "id",
        "characters": "id",
        "aliases": "id",
        "titles": "id",
        "relationships": "id",
        "locations": "id",
        "organizations": "id",
        "organization_relationships": "id",
        "character_locations": None,  # composite PK
        "character_organizations": None,  # composite PK
    }
    return pk_map.get(table)


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate SQLite → PostgreSQL")
    parser.add_argument(
        "--source",
        default="murim_dev.db",
        help="Path to SQLite source database (default: murim_dev.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be migrated without writing to Postgres",
    )
    args = parser.parse_args()

    sqlite_path = Path(args.source)
    if not sqlite_path.exists():
        logger.error("SQLite source not found: %s", sqlite_path)
        logger.error("Copy murim_dev.db to the project root before running this script.")
        return 1

    import os

    database_url = os.environ.get("DATABASE_URL")
    if not database_url or "postgresql" not in database_url:
        logger.error("Set DATABASE_URL to a PostgreSQL connection string before running.")
        return 1

    logger.info("Source SQLite: %s", sqlite_path)
    logger.info("Target Postgres: %s", database_url.replace(":murim_password@", ":***@"))
    if args.dry_run:
        logger.info("DRY RUN — no data will be written")

    # Count source rows
    sqlite_counts = get_sqlite_counts(sqlite_path)
    logger.info("\n── Source SQLite row counts ─────────────────────────")
    total_source = 0
    for table, count in sqlite_counts.items():
        logger.info("  %-35s %6d rows", table, count)
        total_source += count
    logger.info("  %-35s %6d total", "", total_source)

    pg_engine = create_engine(database_url)
    sqlite_conn = sqlite3.connect(str(sqlite_path))

    try:
        logger.info("\n── Migrating tables ─────────────────────────────────")
        results: dict[str, tuple[int, int]] = {}

        for table in MIGRATION_ORDER:
            if table not in sqlite_counts:
                logger.warning("Table %s not found in SQLite — skipping", table)
                continue
            logger.info("Migrating %s (%d rows)...", table, sqlite_counts[table])
            migrated, skipped = migrate_table(table, sqlite_conn, pg_engine, dry_run=args.dry_run)
            results[table] = (migrated, skipped)
            logger.info("  → %d migrated, %d skipped (already existed)", migrated, skipped)

        logger.info("\n── Verification: comparing row counts ───────────────")
        all_ok = True
        with pg_engine.connect() as pg_conn:
            for table in MIGRATION_ORDER:
                if table not in sqlite_counts:
                    continue
                pg_count = pg_conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()  # noqa: S608
                src_count = sqlite_counts[table]
                status = "✅" if pg_count == src_count else "❌ MISMATCH"
                if pg_count != src_count:
                    all_ok = False
                logger.info(
                    "  %-35s SQLite=%6d  Postgres=%6d  %s",
                    table,
                    src_count,
                    pg_count,
                    status,
                )

        if all_ok:
            logger.info("\n✅ Migration complete — all counts match.")
            return 0
        else:
            logger.error("\n❌ Count mismatch detected — investigate before proceeding.")
            return 1

    finally:
        sqlite_conn.close()
        pg_engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
