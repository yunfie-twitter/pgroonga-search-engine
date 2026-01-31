# src/crawler/scheduler.py
# Responsibility: Manages URL crawl states, enforces policies (robots, anomaly, priority), and dispatches jobs.

from urllib.parse import urlparse
from datetime import datetime, timezone
from typing import List, Optional
import redis
from src.services.db import DBTransaction
from src.crawler.async_crawler import AsyncCrawlerClient
from src.config.settings import settings
from src.crawler.robots import RobotsTxtHandler
from src.crawler.anomaly_detector import AnomalyDetector

class CrawlScheduler:
    """
    Central logic for autonomous crawling.
    Orchestrates policy checks and job dispatch.
    """

    def __init__(self):
        self.redis = redis.from_url(settings.REDIS.URL)
        self.max_depth = settings.CRAWLER.MAX_DEPTH
        self.default_interval = settings.CRAWLER.DEFAULT_INTERVAL_SECONDS
        self.lock_ttl = settings.CRAWLER.DOMAIN_LOCK_TTL_SECONDS
        self.robots = RobotsTxtHandler()
        self.detector = AnomalyDetector()

    def schedule_initial_url(self, url: str):
        """Register a seed URL."""
        domain = urlparse(url).netloc
        self._register_url(url, 0, domain)

    def process_discovered_links(self, links: List[str], parent_depth: int):
        """
        Registers new links discovered during a crawl.
        """
        next_depth = parent_depth + 1
        if next_depth > self.max_depth:
            return

        for url in links:
            domain = urlparse(url).netloc
            self._register_url(url, next_depth, domain)

    def _register_url(self, url: str, depth: int, domain: str):
        """
        Registers a URL if allowed by policies.
        Calculates initial priority score.
        """
        # 1. Anomaly Check
        if self.detector.is_anomalous(url):
            print(f"[Scheduler] Blocked anomalous URL: {url}")
            return

        # 2. Robots.txt Check (Pre-registration check optional, but saves DB space)
        # We might check this lazily at dispatch time, but checking here filters noise early.
        if not self.robots.can_fetch(url):
            print(f"[Scheduler] Blocked by robots.txt: {url}")
            return

        # 3. Calculate Score
        # Base Score - Depth Penalty
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
            print(f"[Scheduler] Failed to register {url}: {e}")

    def mark_crawled(self, url: str, success: bool):
        """
        Updates URL status, handles error counting, cleanup, and rescheduling.
        """
        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    # 1. Fetch current stats
                    cur.execute("SELECT error_count, depth, score FROM crawl_urls WHERE url = %s", (url,))
                    row = cur.fetchone()
                    if not row: return
                    
                    current_errors, depth, current_score = row
                    
                    if success:
                        status = 'done'
                        interval = self.default_interval
                        new_errors = 0
                        # Boost score on success (reset error penalty)
                        new_score = settings.CRAWLER.BASE_SCORE - (depth * settings.CRAWLER.DEPTH_PENALTY)
                        
                        # Increment Domain Counter for anomaly detection
                        domain = urlparse(url).netloc
                        self.detector.increment_domain_count(domain)
                    else:
                        status = 'error'
                        interval = settings.CRAWLER.ERROR_INTERVAL_SECONDS
                        new_errors = current_errors + 1
                        # Reduce score
                        new_score = current_score - settings.CRAWLER.ERROR_PENALTY

                        # Check for Max Retries -> Logical Delete
                        if new_errors > settings.CRAWLER.MAX_RETRIES:
                            status = 'deleted'
                            print(f"[Scheduler] URL exceeded max retries, marking deleted: {url}")
                            cur.execute("UPDATE crawl_urls SET status = 'deleted', deleted_at = NOW() WHERE url = %s", (url,))
                            # Also remove from search index
                            cur.execute("DELETE FROM web_pages WHERE url = %s", (url,))
                            return # Exit early

                    # Update DB
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
            print(f"[Scheduler] Failed to update status for {url}: {e}")

    def dispatch_pending_jobs(self, limit: int = 10):
        """
        Dispatches jobs based on Priority Score.
        """
        # Order by Score DESC, then Due Date
        sql_fetch = """
            SELECT url, domain, depth 
            FROM crawl_urls 
            WHERE status IN ('pending', 'done', 'error') 
              AND next_crawl_at <= NOW()
            ORDER BY score DESC, next_crawl_at ASC
            LIMIT %s
        """
        
        candidates = []
        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql_fetch, (limit * 5,))
                    candidates = cur.fetchall()
        except Exception as e:
            print(f"[Scheduler] Fetch failed: {e}")
            return

        dispatched_count = 0
        client = AsyncCrawlerClient()
        
        for row in candidates:
            if dispatched_count >= limit:
                break
                
            url, domain, depth = row
            
            # Domain Lock Check
            lock_key = f"crawl_lock:{domain}"
            if self.redis.exists(lock_key):
                continue
                
            # Domain Quota Check
            if self.detector.check_domain_limit(domain):
                print(f"[Scheduler] Domain limit reached for {domain}, skipping.")
                continue

            # Robots.txt Re-check (Just in case policies changed since registration)
            if not self.robots.can_fetch(url):
                print(f"[Scheduler] Blocked by robots.txt at dispatch: {url}")
                self._mark_blocked(url, "robots.txt")
                continue

            if self.redis.set(lock_key, 1, ex=self.lock_ttl, nx=True):
                if self._set_crawling_status(url):
                    client.enqueue_job(url, depth)
                    dispatched_count += 1
                else:
                    self.redis.delete(lock_key)

    def _set_crawling_status(self, url: str) -> bool:
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

    def _mark_blocked(self, url: str, reason: str):
        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE crawl_urls SET status = 'blocked', blocked_reason = %s, updated_at = NOW() WHERE url = %s",
                        (reason, url)
                    )
        except Exception:
            pass
