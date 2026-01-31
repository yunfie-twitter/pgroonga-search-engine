# src/crawler/frequency.py
# Responsibility: Manages crawl scheduling metadata to enforce frequency limits per URL.

from datetime import datetime, timezone
from typing import Optional

from src.services.db import DBTransaction


class CrawlFrequencyManager:
    """
    Enforces policies on how often a specific URL can be crawled.
    Interacts with the 'crawl_metadata' table.
    """

    @staticmethod
    def is_crawl_allowed(url: str) -> bool:
        """
        Determines if the URL is eligible for crawling at this moment.
        If it's a new URL, it records it and allows crawling.
        """
        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    # 1. Ensure record exists (Atomic UPSERT for initial tracking)
                    sql_init = """
                        INSERT INTO crawl_metadata (url, next_crawl_at, status)
                        VALUES (%s, NOW(), 'pending')
                        ON CONFLICT (url) DO NOTHING
                    """
                    cur.execute(sql_init, (url,))

                    # 2. Check Schedule
                    sql_check = "SELECT next_crawl_at FROM crawl_metadata WHERE url = %s"
                    cur.execute(sql_check, (url,))
                    row = cur.fetchone()

                    if not row:
                        return True # Should not happen due to insert above

                    next_crawl_at = row[0]
                    # Ensure UTC comparison if DB returns aware datetime
                    if next_crawl_at <= datetime.now(timezone.utc):
                        return True
                    else:
                        print(f"[Frequency] Skipping {url}. Next allowed: {next_crawl_at}")
                        return False

        except Exception as e:
            print(f"[Frequency] Check failed: {e}")
            # Fail safe: Deny crawl to prevent spamming on DB errors
            return False

    @staticmethod
    def update_crawl_status(url: str, success: bool, error_message: Optional[str] = None):
        """
        Updates the metadata after a crawl attempt, setting the next allowed crawl time.
        """
        status = 'completed' if success else 'failed'

        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    sql = """
                        UPDATE crawl_metadata
                        SET
                            last_crawled_at = NOW(),
                            -- Schedule next crawl: NOW + interval
                            next_crawl_at = NOW() + (crawl_interval_minutes * INTERVAL '1 minute'),
                            status = %s,
                            error_message = %s,
                            updated_at = NOW()
                        WHERE url = %s
                    """
                    cur.execute(sql, (status, error_message, url))
        except Exception as e:
            print(f"[Frequency] Status update failed: {e}")
