"""
Database factory - selects SQLite or PostgreSQL backend based on DB_TYPE env var.

Usage in application code:
    from app.models.db_factory import db, get_db_connection, init_db, verify_password

DB_TYPE=sqlite  (default) -> uses existing database.py (SQLite)
DB_TYPE=postgres          -> uses db_postgres.py (PostgreSQL)

Environment variables for PostgreSQL:
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""

import os
from dotenv import load_dotenv

load_dotenv()

DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()

if DB_TYPE == "postgres":
    from app.models.db_postgres import (
        SimpleDB,
        get_db_connection,
        init_db,
        hash_password,
        verify_password,
    )

    db = SimpleDB()
    # PostgreSQL does not use DB_PATH, but expose a sentinel for compatibility
    DB_PATH = None
else:
    from app.models.database import (
        SimpleDB,
        get_db_connection,
        init_db,
        hash_password,
        verify_password,
        DB_PATH,
    )

    db = SimpleDB()

__all__ = [
    "db",
    "SimpleDB",
    "get_db_connection",
    "init_db",
    "hash_password",
    "verify_password",
    "DB_PATH",
    "DB_TYPE",
]
