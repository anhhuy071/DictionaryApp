import os
import csv
import re
import html
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import IntegrityError

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext


def replace_br_and_plus(text):
    text = text.replace('<br />', '\n').replace('<br>=', '\n')
    return text


def convert_html_chars(text):
    return html.unescape(text)


def main():
    try:
        with open("dataapp.csv", "r", encoding="utf-8", errors='ignore') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                word_id, word, pronunciation, meaning, description = row[:5]
                example = row[5] if len(row) > 5 else None

                word = convert_html_chars(replace_br_and_plus(clean_html(word)))
                pronunciation = convert_html_chars(replace_br_and_plus(clean_html(pronunciation)))
                meaning = convert_html_chars(replace_br_and_plus(clean_html(meaning)))
                description = convert_html_chars(replace_br_and_plus(clean_html(description)))
                if example:
                    example = convert_html_chars(replace_br_and_plus(clean_html(example)))

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
                    print(f"Added word: {word}")
                except IntegrityError:
                    print(f"Word {word} already exists in the database.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == '__main__':
    main()
