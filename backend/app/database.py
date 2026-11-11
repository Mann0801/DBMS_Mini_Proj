"""Database connection helper.

Usage in a route:

    with get_db() as conn:
        result = some_service(conn, ...)

The block commits if it finishes normally, rolls back if anything raises,
and always closes the connection.
"""

import os
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Open a new connection using the settings in .env."""
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "campuseats"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "campuseats"),
        charset="utf8mb4",
        cursorclass=DictCursor,  # rows come back as dicts
        autocommit=False,        # we commit / roll back ourselves
    )


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
