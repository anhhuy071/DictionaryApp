import os
import csv
import re
import html
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import IntegrityError

load_dotenv()

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

DEFAULT_CSV = Path("dataapp.csv")


def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)


def normalize_field(text):
    if not text:
        return text
    text = text.replace('<br />', '\n').replace('<br>=', '\n')
    text = clean_html(text)
    return html.unescape(text)


def main():
    csv_path = Path(os.getenv("CSV_PATH", DEFAULT_CSV))
    if not csv_path.is_file():
        print(f"CSV file not found: {csv_path}")
        return

    inserted = 0
    skipped = 0

    with csv_path.open("r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) < 5:
                continue

            word_id, word, pronunciation, meaning, description = row[:5]
            example = row[5] if len(row) > 5 else None

            word = normalize_field(word)
            pronunciation = normalize_field(pronunciation)
            meaning = normalize_field(meaning)
            description = normalize_field(description)
            example = normalize_field(example) if example else None

            if not word or not meaning:
                continue

            try:
                db.execute(
                    text(
                        "INSERT INTO Vocabulary (word, pronunciation, meaning, description, example) "
                        "VALUES (:word, :pronunciation, :meaning, :description, :example)"
                    ),
                    {
                        "word": word,
                        "pronunciation": pronunciation,
                        "meaning": meaning,
                        "description": description,
                        "example": example,
                    },
                )
                db.commit()
                inserted += 1
            except IntegrityError:
                db.rollback()
                skipped += 1

    print(f"Done. Inserted: {inserted}, skipped: {skipped}")


if __name__ == '__main__':
    main()
