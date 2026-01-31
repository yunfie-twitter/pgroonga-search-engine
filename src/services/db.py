import psycopg2
from typing import Generator
from src.config.settings import settings

def get_db_connection():
    """
    Creates and returns a raw psycopg2 connection.
    Used by services that need direct DB access.
    """
    conn = psycopg2.connect(settings.DATABASE_URL)
    conn.autocommit = False  # Explicit transaction management
    return conn

class DBConnection:
    """
    Context manager for database connections to ensure proper closing.
    """
    def __enter__(self):
        self.conn = get_db_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()
