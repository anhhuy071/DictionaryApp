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

### Optional: import vocabulary CSV

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

## Manual setup
1. Clone the repository
2. In your terminal window, navigate into the project
3. Run `pip3 install -r requirements.txt` to make sure all of the necessary Python packages (Flask, SQLAlchemy and others) are installed
4. Set the environment variables:
	* `export FLASK_APP=application.py`. On Windows, the command is instead `set FLASK_APP=application.py`
    - `DATABASE_URL` = URI for your local postgreSQL database (for example: `postgres://username:password@localhost:5432/databasename` )
5. Run `tables.sql` against your database to create the necessary tables
  
6. Run `python3 import.py` to import a spreadsheet in CSV format to your database
7. Finally execute `flask run` command in your terminal to start the server