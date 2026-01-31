# src/crawler/anomaly_detector.py
# Responsibility: Detecting abnormal crawling patterns (spider traps, infinite loops).

from urllib.parse import urlparse
import redis
from src.config.settings import settings

class AnomalyDetector:
    """
    Guards against spider traps and infinite URL generation.
    """

    def __init__(self):
        self.redis = redis.from_url(settings.REDIS.URL)
        self.max_repeats = settings.CRAWLER.MAX_PATH_SEGMENT_REPEATS
        self.max_length = settings.CRAWLER.MAX_URL_LENGTH

    def is_anomalous(self, url: str) -> bool:
        """
        Checks if a URL looks suspicious.
        """
        # 1. Length Check
        if len(url) > self.max_length:
            return True

        # 2. Path Segment Repetition (e.g. /cal/cal/cal/cal)
        path = urlparse(url).path
        segments = [s for s in path.split('/') if s]
        if not segments:
            return False
            
        # Check for immediate repeats
        repeat_count = 0
        last_segment = None
        for seg in segments:
            if seg == last_segment:
                repeat_count += 1
            else:
                repeat_count = 0
            
            if repeat_count >= self.max_repeats:
                return True
            last_segment = seg
            
        return False

    def check_domain_limit(self, domain: str) -> bool:
        """
        Checks if we've crawled too many URLs for this domain recently.
        Uses Redis counter.
        """
        key = f"stats:domain_count:{domain}"
        count = self.redis.get(key)
        if count and int(count) > settings.CRAWLER.MAX_URLS_PER_DOMAIN:
            return True # Blocked
        
        return False

    def increment_domain_count(self, domain: str):
        """
        Increments the crawl counter for a domain.
        TTL 24h to reset daily quotas.
        """
        key = f"stats:domain_count:{domain}"
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 86400) # 24h window
        pipe.execute()
