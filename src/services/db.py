# src/services/db.py
# Responsibility: Provides centralized database connection management and transaction handling.


import psycopg2

from src.config.settings import settings


def get_raw_connection():
    """
    Creates and returns a raw psycopg2 connection.
    Used by internal services that require direct DB access.

    Returns:
        psycopg2.extensions.connection: A new database connection.
    """
    conn = psycopg2.connect(settings.DB.URL)
    conn.autocommit = False  # Explicit transaction management is safer for production
    return conn

class DBTransaction:
    """
    Context manager for database transactions.
    Ensures that commits happen on success and rollbacks happen on exception.
    Also ensures connections are closed properly to prevent leaks.

    Usage:
        with DBTransaction() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
    """
    def __init__(self):
        self.conn = None

    def __enter__(self):
        try:
            self.conn = get_raw_connection()
            return self.conn
        except Exception as e:
            # If connection fails, ensure we don't return a broken state
            print(f"[DB] Connection failed: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            try:
                if exc_type:
                    # An exception occurred within the block -> Rollback
                    self.conn.rollback()
                    print(f"[DB] Transaction rolled back due to error: {exc_val}")
                else:
                    # No exception -> Commit
                    self.conn.commit()
            except Exception as e:
                print(f"[DB] Transaction finalization failed: {e}")
                # We do not suppress the original exception if there was one
            finally:
                self.conn.close()

# Alias for simpler import usage if desired, though class usage is preferred for explicitness
get_db_connection = get_raw_connection
