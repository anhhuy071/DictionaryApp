# DictionaryApp
Project learning for school

## Docker (recommended)

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. From the project root, run:

```bash
docker compose up --build
```

3. Open http://localhost:5000

The database schema from `tables.sql` is applied automatically on first startup.

### Import vocabulary (recommended)

Use the free English → Vietnamese dataset from [minhqnd/dictionary](https://github.com/minhqnd/dictionary/releases) (CC BY-SA 4.0):

1. Download `dictionary.db` from the releases page
2. Place it at `data/dictionary.db`
3. Import:

```bash
docker compose exec web python import_minhqnd.py
```

For a quick test with 1000 words:

```bash
docker compose exec web python import_minhqnd.py --limit 1000
```

### Legacy CSV import

Place `dataapp.csv` in the project root, then run:

```bash
docker compose exec web python import.py
```

### Useful commands

```bash
docker compose down          # stop containers
docker compose down -v       # stop and remove database volume (fresh start)
docker compose logs -f web   # follow app logs
```

Copy `.env.example` to `.env` if you run the app outside Docker.

## Data licensing

Vocabulary imported via `import_minhqnd.py` comes from [dict.minhqnd.com](https://dict.minhqnd.com) and is licensed under **CC BY-SA 4.0**. Keep the attribution in the app footer when using this data.

## Manual setup

1. Clone the repository
2. In your terminal window, navigate into the project
3. Run `pip3 install -r requirements.txt` to make sure all of the necessary Python packages (Flask, SQLAlchemy and others) are installed
4. Set the environment variables:
   * `export FLASK_APP=application.py`. On Windows, the command is instead `set FLASK_APP=application.py`
   - `DATABASE_URL` = URI for your local postgreSQL database (for example: `postgres://username:password@localhost:5432/databasename` )
5. Run `tables.sql` against your database to create the necessary tables
6. Download `dictionary.db` to `data/` and run `python import_minhqnd.py`
7. Finally execute `flask run` command in your terminal to start the server
