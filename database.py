import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

# In Docker, DATABASE_URL env var is set by docker-compose.
# Locally, falls back to your SQL Server Express instance.
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    r"mssql+pyodbc://@localhost\SQLEXPRESS/Student_db"
    "?driver=ODBC+Driver+17+for+SQL+Server"
    "&trusted_connection=yes"
)


def ensure_sql_server_database(database_url: str):
    url = make_url(database_url)

    if not url.drivername.startswith("mssql") or not url.database:
        return

    database_name = url.database
    master_url = url.set(database="master")
    master_engine = create_engine(master_url, isolation_level="AUTOCOMMIT")

    with master_engine.connect() as connection:
        exists = connection.execute(
            text("SELECT DB_ID(:database_name)"),
            {"database_name": database_name},
        ).scalar()

        if exists is None:
            safe_database_name = database_name.replace("]", "]]")
            connection.execute(text(f"CREATE DATABASE [{safe_database_name}]"))


ensure_sql_server_database(SQLALCHEMY_DATABASE_URL)
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
