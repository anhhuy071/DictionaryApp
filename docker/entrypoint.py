import os
import sys
import time

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError


def wait_for_database():
    url = os.environ["DATABASE_URL"]
    engine = create_engine(url)

    for _ in range(30):
        try:
            with engine.connect():
                return
        except OperationalError:
            time.sleep(1)

    sys.exit("Database is not ready")


def main():
    print("Waiting for database...")
    wait_for_database()
    print("Starting application...")
    os.execvp(
        "gunicorn",
        [
            "gunicorn",
            "--bind",
            "0.0.0.0:5000",
            "--workers",
            "2",
            "--threads",
            "4",
            "application:app",
        ],
    )


if __name__ == "__main__":
    main()
