# Dictionary App

English → Vietnamese dictionary and vocabulary learning web app built with Flask and PostgreSQL.

Look up words with pronunciation and Vietnamese meanings, browse the dictionary, and (when logged in) create word lists with flashcards, quizzes, and progress tracking.

## Features

- **Dictionary lookup** — search by English word, ranked results, word detail pages
- **Browse** — paginated vocabulary list
- **My lists** — save words to custom vocabulary pages (login required)
- **Study modes** — flashcards, quizzes, matching game
- **Mobile-friendly UI** — responsive search and results

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend | Python, Flask, Gunicorn |
| Database | PostgreSQL, SQLAlchemy |
| Frontend | Jinja2, Bootstrap 5 |
| Deploy | Docker Compose |

## Quick start (Docker)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### 1. Clone and start

```bash
git clone https://github.com/anhhuy071/DictionaryApp.git
cd DictionaryApp
docker compose up --build
```

Open **http://localhost:5000**

On first startup, PostgreSQL runs `tables.sql` automatically and the app seeds **25 sample words** if the dictionary is empty.

### 2. Import full vocabulary (recommended)

The app needs imported data for a useful dictionary. Use the free dataset from [minhqnd/dictionary](https://github.com/minhqnd/dictionary/releases):

```bash
# Download dictionary.db from the releases page, then:
mkdir -p data
# move the file to data/dictionary.db

docker compose exec web python import_minhqnd.py --fresh --db /app/data/dictionary.db
```

| Flag | Description |
|------|-------------|
| `--fresh` | Clear existing vocabulary, then import |
| `--limit 1000` | Import only N words (for testing) |
| `--db PATH` | SQLite file path (default: `data/dictionary.db`) |

Import reads English words with Vietnamese meanings from SQLite and writes them into PostgreSQL. A full run typically imports **~118k words** in about 1–2 minutes.

### 3. Verify

```bash
docker compose exec db psql -U dictionary -d dictionary -c "SELECT COUNT(*) FROM vocabulary;"
```

Try searching: http://localhost:5000/search?q=hello

## How import works

```
dictionary.db (SQLite)  →  import_minhqnd.py  →  PostgreSQL (vocabulary table)  →  Flask app
```

| App column | Source |
|------------|--------|
| `word` | English entry |
| `pronunciation` | IPA |
| `meaning` | Vietnamese translation / definition |
| `description` | Part of speech |
| `example` | Example sentence |

Data is **not** bundled in the repo. Download `dictionary.db` separately (~171 MB). The file is gitignored at `data/dictionary.db`.

### Legacy CSV import

If you have `dataapp.csv` (columns: word, pronunciation, meaning, description, example):

```bash
docker compose exec web python import.py
```

## Local development (without Docker)

### 1. Install dependencies

```bash
python -m venv myenv
myenv\Scripts\activate        # Windows
# source myenv/bin/activate   # macOS / Linux

pip install -r requirements.txt
```

### 2. Configure environment

Copy the example env file and edit as needed:

```bash
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux
```

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection URI |
| `SECRET_KEY` | Flask session secret |
| `SESSION_FILE_DIR` | Path for session files |
| `LOG_LEVEL` | Logging level (`INFO`, `DEBUG`) |

### 3. Create database schema

Create a PostgreSQL database, then run:

```bash
psql -U your_user -d your_db -f tables.sql
```

### 4. Import vocabulary

```bash
python import_minhqnd.py --fresh
```

### 5. Run the app

```bash
set FLASK_APP=application.py   # Windows
flask run
```

For production-like local runs:

```bash
gunicorn --bind 0.0.0.0:5000 application:app
```

## Docker commands

```bash
docker compose up --build      # start
docker compose down            # stop
docker compose down -v         # stop and wipe database (fresh start)
docker compose logs -f web     # follow app logs
docker compose exec web bash   # shell inside web container
```

## Project structure

```
DictionaryApp/
├── application.py          # Flask routes and app logic
├── tables.sql              # PostgreSQL schema
├── import_minhqnd.py       # Import from minhqnd dictionary.db (recommended)
├── import.py               # Import from CSV
├── seed_vocabulary.py      # Dev sample words when DB is empty
├── docker-compose.yml
├── Dockerfile
├── data/
│   └── dictionary.db       # Download separately (gitignored)
├── templates/              # Jinja2 HTML pages
└── static/                 # CSS, JS, assets
```

## Data licensing

Vocabulary imported via `import_minhqnd.py` comes from [dict.minhqnd.com](https://dict.minhqnd.com) / [minhqnd/dictionary](https://github.com/minhqnd/dictionary) and is licensed under **CC BY-SA 4.0**.

When using this data, keep the attribution shown in the app footer.

## Troubleshooting

**Search returns no results**
- The vocabulary table is empty. Run the import steps above.

**Import fails: file not found**
- Ensure `dictionary.db` is at `data/dictionary.db` on the host (mounted into the container at `/app/data/`).

**Database reset**
```bash
docker compose down -v
docker compose up --build
docker compose exec web python import_minhqnd.py --fresh --db /app/data/dictionary.db
```

**Port 5000 already in use**
- Change the port in `docker-compose.yml`: `"8080:5000"`, then open http://localhost:8080
