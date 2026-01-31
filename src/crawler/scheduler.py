# src/crawler/scheduler.py
# Responsibility: Orchestrates job dispatching. 
# Delegates state management to Repository to avoid circular imports.

import redis
from src.crawler.async_crawler import AsyncCrawlerClient
from src.config.settings import settings
from src.crawler.repository import CrawlRepository
from src.crawler.robots import RobotsTxtHandler
from src.crawler.anomaly_detector import AnomalyDetector
from urllib.parse import urlparse

class CrawlScheduler:
    """
    Manager class that determines WHAT to run next.
    Does NOT handle the execution or result processing directly.
    """

    def __init__(self):
        self.redis = redis.from_url(settings.REDIS.URL)
        self.lock_ttl = settings.CRAWLER.DOMAIN_LOCK_TTL_SECONDS
        self.repository = CrawlRepository()
        self.detector = AnomalyDetector()
        self.robots = RobotsTxtHandler()

    def schedule_initial_url(self, url: str):
        """Pass-through to repository."""
        self.repository.register_seed_url(url)

    def dispatch_pending_jobs(self, limit: int = 10):
        """
        Main loop logic: Fetches pending URLs and sends them to RQ.
        """
        # 1. Fetch Candidates via Repository
        candidates = self.repository.fetch_pending_jobs(limit)
        
        dispatched_count = 0
        client = AsyncCrawlerClient()
        
        for row in candidates:
            if dispatched_count >= limit:
                break
                
            url, domain, depth = row
            
            # 2. Domain Checks (Lock & Quota)
            lock_key = f"crawl_lock:{domain}"
            if self.redis.exists(lock_key):
                continue
                
            if self.detector.check_domain_limit(domain):
                print(f"[Scheduler] Domain limit reached for {domain}, skipping.")
                continue

            # 3. Final Robots Check
            if not self.robots.can_fetch(url):
                print(f"[Scheduler] Blocked by robots.txt at dispatch: {url}")
                self.repository.mark_blocked(url, "robots.txt")
                continue

            # 4. Acquire Lock & Dispatch
            if self.redis.set(lock_key, 1, ex=self.lock_ttl, nx=True):
                # Update status to 'crawling' via Repository
                if self.repository.set_crawling_status(url):
                    # Enqueue Job
                    client.enqueue_job(url, depth)
                    dispatched_count += 1
                else:
                    self.redis.delete(lock_key)
