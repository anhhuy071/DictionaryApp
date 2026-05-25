"""
Import English → Vietnamese vocabulary from minhqnd/dictionary SQLite database.

Data source: https://github.com/minhqnd/dictionary/releases
License: CC BY-SA 4.0 — attribution required (see README).

Usage:
  set DATABASE_URL=postgresql://...
  python import_minhqnd.py
  python import_minhqnd.py --db data/dictionary.db --limit 1000
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker

load_dotenv()

DEFAULT_DB_PATH = Path("data/dictionary.db")
BATCH_SIZE = 500


def get_sqlite_connection(db_path: Path) -> sqlite3.Connection:
    if not db_path.is_file():
        raise FileNotFoundError(
            f"Dictionary database not found at {db_path}.\n"
            "Download dictionary.db from https://github.com/minhqnd/dictionary/releases "
            "and place it in the data/ folder."
        )
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_english_entries(conn: sqlite3.Connection, limit: int | None = None) -> list[dict]:
    query = """
        SELECT
            w.id,
            w.word,
            (
                SELECT GROUP_CONCAT(DISTINCT p.ipa)
                FROM pronunciations p
                WHERE p.word_id = w.id AND p.ipa IS NOT NULL AND p.ipa != ''
            ) AS ipa,
            (
                SELECT GROUP_CONCAT(DISTINCT t.translation, ' | ')
                FROM translations t
                WHERE t.word_id = w.id AND t.lang_code = 'vi'
                  AND t.translation IS NOT NULL AND t.translation != ''
            ) AS vi_translations,
            (
                SELECT GROUP_CONCAT(DISTINCT d.definition, ' | ')
                FROM word_definitions wd
                JOIN definitions d ON d.id = wd.definition_id
                WHERE wd.word_id = w.id
                  AND COALESCE(d.definition_lang, 'vi') = 'vi'
                  AND d.definition IS NOT NULL AND d.definition != ''
            ) AS vi_definitions,
            (
                SELECT wd.example
                FROM word_definitions wd
                WHERE wd.word_id = w.id
                  AND wd.example IS NOT NULL AND wd.example != ''
                LIMIT 1
            ) AS example,
            (
                SELECT GROUP_CONCAT(DISTINCT
                    TRIM(COALESCE(d.pos, '') || CASE WHEN d.sub_pos IS NOT NULL THEN ' (' || d.sub_pos || ')' ELSE '' END),
                    '; '
                )
                FROM word_definitions wd
                JOIN definitions d ON d.id = wd.definition_id
                WHERE wd.word_id = w.id
                  AND (d.pos IS NOT NULL OR d.sub_pos IS NOT NULL)
            ) AS pos_tags
        FROM words w
        WHERE w.lang_code = 'en'
          AND w.word IS NOT NULL AND w.word != ''
        ORDER BY w.word
    """
    if limit:
        query += f" LIMIT {int(limit)}"

    rows = conn.execute(query).fetchall()
    entries = []
    for row in rows:
        meaning = row["vi_translations"] or row["vi_definitions"]
        if not meaning:
            continue

        description_parts = []
        if row["pos_tags"]:
            description_parts.append(row["pos_tags"])
        if row["vi_definitions"] and row["vi_translations"]:
            description_parts.append(row["vi_definitions"])

        entries.append({
            "word": row["word"].strip(),
            "pronunciation": (row["ipa"] or "").strip() or None,
            "meaning": meaning.strip(),
            "description": " · ".join(description_parts) if description_parts else None,
            "example": (row["example"] or "").strip() or None,
        })
    return entries


def import_to_postgres(entries: list[dict], db_url: str, skip_existing: bool = True) -> tuple[int, int, int]:
    engine = create_engine(db_url)
    session = scoped_session(sessionmaker(bind=engine))

    inserted = 0
    skipped = 0
    errors = 0

    insert_sql = text("""
        INSERT INTO Vocabulary (word, pronunciation, meaning, description, example)
        VALUES (:word, :pronunciation, :meaning, :description, :example)
    """)
    exists_sql = text("SELECT 1 FROM Vocabulary WHERE LOWER(word) = LOWER(:word) LIMIT 1")

    batch: list[dict] = []
    for entry in entries:
        if skip_existing:
            if session.execute(exists_sql, {"word": entry["word"]}).fetchone():
                skipped += 1
                continue
        batch.append(entry)

        if len(batch) >= BATCH_SIZE:
            inserted, errors = _flush_batch(session, insert_sql, batch, inserted, errors)
            batch = []

    if batch:
        inserted, errors = _flush_batch(session, insert_sql, batch, inserted, errors)

    session.remove()
    return inserted, skipped, errors


def _flush_batch(session, insert_sql, batch, inserted, errors):
    for entry in batch:
        try:
            session.execute(insert_sql, entry)
            session.commit()
            inserted += 1
        except Exception as exc:
            session.rollback()
            errors += 1
            print(f"Error importing '{entry['word']}': {exc}", file=sys.stderr)
    return inserted, errors


def main():
    parser = argparse.ArgumentParser(description="Import EN→VI vocabulary from minhqnd dictionary.db")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Path to dictionary.db")
    parser.add_argument("--limit", type=int, default=None, help="Max words to import (for testing)")
    parser.add_argument("--allow-duplicates", action="store_true", help="Insert even if word already exists")
    args = parser.parse_args()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        sys.exit(1)

    print(f"Reading from {args.db}...")
    conn = get_sqlite_connection(args.db)
    entries = fetch_english_entries(conn, limit=args.limit)
    conn.close()
    print(f"Found {len(entries)} English entries with Vietnamese meanings.")

    if not entries:
        print("Nothing to import.")
        sys.exit(0)

    print("Importing into PostgreSQL...")
    inserted, skipped, errors = import_to_postgres(
        entries, db_url, skip_existing=not args.allow_duplicates
    )

    print(f"Done. Inserted: {inserted}, skipped (existing): {skipped}, errors: {errors}")


if __name__ == "__main__":
    main()
