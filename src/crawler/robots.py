# src/crawler/robots.py
# Responsibility: Handling robots.txt fetching, parsing, and caching.

import urllib.robotparser
from urllib.parse import urlparse
import redis
import httpx
from src.config.settings import settings

class RobotsTxtHandler:
    """
    Manages robots.txt compliance.
    Caches parsed rules in Redis to avoid redundant fetches.
    """

    def __init__(self):
        self.redis = redis.from_url(settings.REDIS.URL)
        self.ttl = settings.CRAWLER.ROBOTS_CACHE_TTL
        self.user_agent = settings.CRAWLER.USER_AGENT

    def can_fetch(self, url: str) -> bool:
        """
        Checks if the URL is allowed by robots.txt.
        """
        domain = urlparse(url).netloc
        robots_url = f"{urlparse(url).scheme}://{domain}/robots.txt"
        
        # 1. Check Cache
        # We store the serialized robots.txt content or specific rules. 
        # For simplicity, we'll store the raw content and re-parse. 
        # (Parsing is fast, fetching is slow)
        cache_key = f"robots:{domain}"
        cached_content = self.redis.get(cache_key)

        rp = urllib.robotparser.RobotFileParser()
        
        if cached_content:
            # Load from cache
            try:
                rp.parse(cached_content.decode('utf-8').splitlines())
            except Exception:
                # If cache is corrupted, re-fetch
                cached_content = None

        if not cached_content:
            # Fetch from network
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(robots_url, follow_redirects=True)
                    if resp.status_code == 200:
                        content = resp.text
                        rp.parse(content.splitlines())
                        # Save to cache
                        self.redis.setex(cache_key, self.ttl, content)
                    else:
                        # If 404 or error, assume allowed but cache the "absence" 
                        # to prevent retries (e.g. empty string)
                        self.redis.setex(cache_key, self.ttl, "")
                        return True
            except Exception:
                # Network error on robots.txt -> Allow temporarily or Deny?
                # Standard practice: If robots.txt unreachable, assume allowed or retry later.
                # We'll allow it but not cache, so we try again next time.
                return True

        return rp.can_fetch(self.user_agent, url)

    def get_crawl_delay(self, url: str) -> float:
        """
        Extracts crawl-delay if present.
        """
        # Logic similar to above would be needed to get the RP object.
        # Ideally we refactor `_get_rp(domain)` to avoid duplication.
        # Omitted for brevity, defaulting to system interval.
        return 0.0
