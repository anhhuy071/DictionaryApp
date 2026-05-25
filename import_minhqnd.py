"""
Import English → Vietnamese vocabulary from minhqnd/dictionary SQLite database.

Data source: https://github.com/minhqnd/dictionary/releases
License: CC BY-SA 4.0 — attribution required (see README).
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker

load_dotenv()

DEFAULT_DB_PATH = Path("data/dictionary.db")
BATCH_SIZE = 1000

FETCH_QUERY = """
    SELECT
        w.word,
        (
            SELECT GROUP_CONCAT(DISTINCT p.ipa)
            FROM pronunciations p
            WHERE p.word_id = w.id AND p.ipa IS NOT NULL AND p.ipa != ''
        ) AS ipa,
        COALESCE(
            (
                SELECT GROUP_CONCAT(DISTINCT t.translation)
                FROM translations t
                WHERE t.word_id = w.id AND t.lang_code = 'vi'
                  AND t.translation IS NOT NULL AND t.translation != ''
            ),
            (
                SELECT GROUP_CONCAT(DISTINCT d.definition)
                FROM word_definitions wd
                JOIN definitions d ON d.id = wd.definition_id
                WHERE wd.word_id = w.id
                  AND COALESCE(d.definition_lang, 'vi') = 'vi'
                  AND d.definition IS NOT NULL AND d.definition != ''
            )
        ) AS meaning,
        (
            SELECT GROUP_CONCAT(DISTINCT
                TRIM(COALESCE(d.pos, '') || CASE WHEN d.sub_pos IS NOT NULL THEN ' (' || d.sub_pos || ')' ELSE '' END)
            )
            FROM word_definitions wd
            JOIN definitions d ON d.id = wd.definition_id
            WHERE wd.word_id = w.id
              AND (d.pos IS NOT NULL OR d.sub_pos IS NOT NULL)
        ) AS pos_tags,
        (
            SELECT wd.example
            FROM word_definitions wd
            WHERE wd.word_id = w.id
              AND wd.example IS NOT NULL AND wd.example != ''
            LIMIT 1
        ) AS example
    FROM words w
    WHERE w.lang_code = 'en'
      AND w.word IS NOT NULL AND w.word != ''
      AND (
          EXISTS (
              SELECT 1 FROM translations t
              WHERE t.word_id = w.id AND t.lang_code = 'vi'
                AND t.translation IS NOT NULL AND t.translation != ''
          )
          OR EXISTS (
              SELECT 1 FROM word_definitions wd
              JOIN definitions d ON d.id = wd.definition_id
              WHERE wd.word_id = w.id
                AND COALESCE(d.definition_lang, 'vi') = 'vi'
                AND d.definition IS NOT NULL AND d.definition != ''
          )
      )
    ORDER BY w.word
"""


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


def clear_vocabulary(db_url: str) -> None:
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE learningprogress RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE vocabulary RESTART IDENTITY CASCADE"))
    print("Cleared existing vocabulary and learning progress.")


def row_to_entry(row: sqlite3.Row) -> dict | None:
    meaning = row["meaning"]
    if not meaning:
        return None
    return {
        "word": row["word"].strip(),
        "pronunciation": (row["ipa"] or "").strip() or None,
        "meaning": meaning.strip(),
        "description": (row["pos_tags"] or "").strip() or None,
        "example": (row["example"] or "").strip() or None,
    }


def import_stream(conn: sqlite3.Connection, db_url: str, limit: int | None = None) -> tuple[int, int]:
    engine = create_engine(db_url)
    session = scoped_session(sessionmaker(bind=engine))
    insert_sql = text("""
        INSERT INTO vocabulary (word, pronunciation, meaning, description, example)
        VALUES (:word, :pronunciation, :meaning, :description, :example)
    """)

    query = FETCH_QUERY
    if limit:
        query += f" LIMIT {int(limit)}"

    inserted = 0
    errors = 0
    batch: list[dict] = []
    started = time.time()

    for row in conn.execute(query):
        entry = row_to_entry(row)
        if not entry:
            continue
        batch.append(entry)
        if len(batch) >= BATCH_SIZE:
            inserted, errors = _flush_batch(session, insert_sql, batch, inserted, errors)
            batch = []
            if inserted % 10000 == 0:
                elapsed = time.time() - started
                print(f"  ... {inserted:,} words imported ({elapsed:.0f}s)")

    if batch:
        inserted, errors = _flush_batch(session, insert_sql, batch, inserted, errors)

    session.remove()
    return inserted, errors


def _flush_batch(session, insert_sql, batch, inserted, errors):
    try:
        for entry in batch:
            session.execute(insert_sql, entry)
        session.commit()
        inserted += len(batch)
    except Exception as exc:
        session.rollback()
        for entry in batch:
            try:
                session.execute(insert_sql, entry)
                session.commit()
                inserted += 1
            except Exception as row_exc:
                session.rollback()
                errors += 1
                print(f"Error importing '{entry['word']}': {row_exc}", file=sys.stderr)
    return inserted, errors


def main():
    parser = argparse.ArgumentParser(description="Import EN→VI vocabulary from minhqnd dictionary.db")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Path to dictionary.db")
    parser.add_argument("--limit", type=int, default=None, help="Max words to import (for testing)")
    parser.add_argument("--fresh", action="store_true", help="Clear existing vocabulary before import")
    args = parser.parse_args()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        sys.exit(1)

    print(f"Reading from {args.db}...")
    if args.fresh:
        clear_vocabulary(db_url)

    conn = get_sqlite_connection(args.db)
    print("Importing into PostgreSQL (this may take several minutes)...")
    started = time.time()
    inserted, errors = import_stream(conn, db_url, limit=args.limit)
    conn.close()
    elapsed = time.time() - started
    print(f"Done in {elapsed:.0f}s. Inserted: {inserted:,}, errors: {errors:,}")


if __name__ == "__main__":
    main()
