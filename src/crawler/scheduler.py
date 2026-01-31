# src/crawler/scheduler.py
# Responsibility: Manages URL crawl states, enforces depth/frequency rules, and dispatches jobs.

from urllib.parse import urlparse
from datetime import datetime, timezone
from typing import List, Optional
import redis
from src.services.db import DBTransaction
from src.crawler.async_crawler import AsyncCrawlerClient
from src.config.settings import settings

class CrawlScheduler:
    """
    Central logic for autonomous crawling.
    Handles URL registration, state updates, and job dispatching.
    """

    def __init__(self):
        self.redis = redis.from_url(settings.REDIS.URL)
        self.max_depth = settings.CRAWLER.MAX_DEPTH
        self.default_interval = settings.CRAWLER.DEFAULT_INTERVAL_SECONDS
        self.lock_ttl = settings.CRAWLER.DOMAIN_LOCK_TTL_SECONDS

    def schedule_initial_url(self, url: str):
        """Register a seed URL with depth 0."""
        self._register_url(url, 0, urlparse(url).netloc)

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
        Idempotent registration of a URL.
        If exists, we do nothing (unless we want to update depth/priority in future).
        """
        sql = """
            INSERT INTO crawl_urls (url, domain, depth, status, next_crawl_at)
            VALUES (%s, %s, %s, 'pending', NOW())
            ON CONFLICT (url) DO NOTHING
        """
        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (url, domain, depth))
        except Exception as e:
            print(f"[Scheduler] Failed to register {url}: {e}")

    def mark_crawled(self, url: str, success: bool):
        """
        Updates URL status after a crawl attempt and schedules next run.
        """
        status = 'done' if success else 'error'
        interval = self.default_interval if success else settings.CRAWLER.ERROR_INTERVAL_SECONDS
        
        sql = """
            UPDATE crawl_urls
            SET status = %s,
                last_crawled_at = NOW(),
                next_crawl_at = NOW() + (%s * INTERVAL '1 second'),
                updated_at = NOW()
            WHERE url = %s
        """
        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (status, interval, url))
        except Exception as e:
            print(f"[Scheduler] Failed to update status for {url}: {e}")

    def dispatch_pending_jobs(self, limit: int = 10):
        """
        Finds pending URLs ready for crawling and dispatches them to RQ.
        Enforces domain-level locking to prevent spamming.
        """
        # 1. Fetch Candidates (pending & time is due)
        # We order by next_crawl_at to prioritize overdue jobs.
        sql_fetch = """
            SELECT url, domain, depth 
            FROM crawl_urls 
            WHERE status IN ('pending', 'done', 'error') 
              AND next_crawl_at <= NOW()
            ORDER BY next_crawl_at ASC
            LIMIT %s
        """
        
        candidates = []
        try:
            with DBTransaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql_fetch, (limit * 5,)) # Fetch more to account for locks
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
            
            # 2. Domain Lock Check (Redis)
            lock_key = f"crawl_lock:{domain}"
            if self.redis.exists(lock_key):
                continue
                
            # 3. Acquire Lock
            if self.redis.set(lock_key, 1, ex=self.lock_ttl, nx=True):
                # 4. Dispatch
                # Optimistically update status to 'crawling' to prevent double-dispatch
                if self._set_crawling_status(url):
                    client.enqueue_job(url, depth) # Updated client method needed
                    dispatched_count += 1
                    print(f"[Scheduler] Dispatched {url}")
                else:
                    self.redis.delete(lock_key) # Release if DB update failed

    def _set_crawling_status(self, url: str) -> bool:
        """Atomic update to 'crawling' state."""
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
