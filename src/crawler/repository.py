# src/crawler/repository.py
# Responsibility: Encapsulates database operations and state transitions for the crawler.
# This module is the "lower layer" that can be imported by both the Job (worker) and Scheduler (manager).

from urllib.parse import urlparse
from typing import List, Tuple
from src.services.db import DBTransaction
from src.config.settings import settings
from src.crawler.robots import RobotsTxtHandler
from src.crawler.anomaly_detector import AnomalyDetector

class CrawlRepository:
    """
    Data Access Layer for Crawler State.
    Handles all interactions with 'crawl_urls' table.
    Includes business logic for registration policies (Robots/Anomaly) to ensure consistency.
    """

    def __init__(self):
        self.robots = RobotsTxtHandler()
        self.detector = AnomalyDetector()

    def register_seed_url(self, url: str):
        """Registers a seed URL (Depth 0)."""
        domain = urlparse(url).netloc
        self._register_url(url, 0, domain)

    def process_discovered_links(self, links: List[str], parent_depth: int):
        """Registers discovered links if they meet depth criteria."""
        next_depth = parent_depth + 1
        if next_depth > settings.CRAWLER.MAX_DEPTH:
            return

        for url in links:
            domain = urlparse(url).netloc
            self._register_url(url, next_depth, domain)

    def _register_url(self, url: str, depth: int, domain: str):
        """
        Internal registration logic with policy checks.
        """
        # 1. Anomaly Check
        if self.detector.is_anomalous(url):
            return

        # 2. Robots.txt Check
        if not self.robots.can_fetch(url):
            return

        # 3. Score Calculation
        score = settings.CRAWLER.BASE_SCORE - (depth * settings.CRAWLER.DEPTH_PENALTY)

        sql = """
            INSERT INTO crawl_urls (url, domain, depth, status, next_crawl_at, score)
            VALUES (%s, %s, %s, 'pending', NOW(), %s)
            ON CONFLICT (url) DO NOTHING
        """
        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (url, domain, depth, score))
        except Exception as e:
            print(f"[Repository] Registration failed for {url}: {e}")

    def mark_crawled(self, url: str, success: bool):
        """
        Updates URL status, handles error counting, and schedules next crawl.
        """
        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    # Fetch current state
                    cur.execute("SELECT error_count, depth, score FROM crawl_urls WHERE url = %s", (url,))
                    row = cur.fetchone()
                    if not row: return
                    
                    current_errors, depth, current_score = row
                    
                    if success:
                        status = 'done'
                        interval = settings.CRAWLER.DEFAULT_INTERVAL_SECONDS
                        new_errors = 0
                        new_score = settings.CRAWLER.BASE_SCORE - (depth * settings.CRAWLER.DEPTH_PENALTY)
                        
                        # Update stats
                        domain = urlparse(url).netloc
                        self.detector.increment_domain_count(domain)
                    else:
                        status = 'error'
                        interval = settings.CRAWLER.ERROR_INTERVAL_SECONDS
                        new_errors = current_errors + 1
                        new_score = current_score - settings.CRAWLER.ERROR_PENALTY

                        # Max Retries Check
                        if new_errors > settings.CRAWLER.MAX_RETRIES:
                            self._delete_url(cur, url)
                            return

                    # Update Status
                    sql = """
                        UPDATE crawl_urls
                        SET status = %s,
                            last_crawled_at = NOW(),
                            next_crawl_at = NOW() + (%s * INTERVAL '1 second'),
                            updated_at = NOW(),
                            error_count = %s,
                            score = %s
                        WHERE url = %s
                    """
                    cur.execute(sql, (status, interval, new_errors, new_score, url))
                    
        except Exception as e:
            print(f"[Repository] Status update failed for {url}: {e}")

    def _delete_url(self, cur, url: str):
        """Logically deletes a URL and removes its index."""
        print(f"[Repository] Deleting {url} due to max errors.")
        cur.execute("UPDATE crawl_urls SET status = 'deleted', deleted_at = NOW() WHERE url = %s", (url,))
        cur.execute("DELETE FROM web_pages WHERE url = %s", (url,))

    def fetch_pending_jobs(self, limit: int) -> List[Tuple]:
        """Fetches pending jobs for the dispatcher."""
        sql = """
            SELECT url, domain, depth 
            FROM crawl_urls 
            WHERE status IN ('pending', 'done', 'error') 
              AND next_crawl_at <= NOW()
            ORDER BY score DESC, next_crawl_at ASC
            LIMIT %s
        """
        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (limit * 5,))
                    return cur.fetchall()
        except Exception:
            return []

    def set_crawling_status(self, url: str) -> bool:
        """Atomic transition to 'crawling'."""
        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE crawl_urls SET status = 'crawling', updated_at = NOW() WHERE url = %s",
                        (url,)
                    )
            return True
        except Exception:
            return False

    def mark_blocked(self, url: str, reason: str):
        """Marks a URL as blocked."""
        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE crawl_urls SET status = 'blocked', blocked_reason = %s, updated_at = NOW() WHERE url = %s",
                        (reason, url)
                    )
        except Exception:
            pass
