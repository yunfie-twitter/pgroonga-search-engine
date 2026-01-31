# src/crawler/async_crawler.py
# Responsibility: Client interface for enqueueing crawl jobs to Redis Queue (RQ).

from typing import Any, Dict, List

import redis
from rq import Queue

from src.config.settings import settings
from src.crawler.job import perform_crawl_job


class AsyncCrawlerClient:
    """
    Facade for interacting with the asynchronous crawler queue.
    """

    def __init__(self):
        self.redis_conn = redis.from_url(settings.REDIS.URL)
        self.queue = Queue(settings.REDIS.QUEUE_NAME, connection=self.redis_conn)

    def enqueue_jobs(self, urls: List[str]) -> List[str]:
        """Legacy support."""
        job_ids = []
        for url in urls:
            job_ids.append(self.enqueue_job(url, depth=0))
        return job_ids

    def enqueue_job(self, url: str, depth: int) -> str:
        """
        Enqueues a single job.
        This module imports 'perform_crawl_job' but 'job.py' does NOT import this module.
        Cycle broken.
        """
        job = self.queue.enqueue(
            perform_crawl_job,
            url,
            depth,
            job_timeout=settings.CRAWLER.JOB_TIMEOUT
        )
        return job.get_id()

    def get_queue_info(self) -> Dict[str, Any]:
        return {
            "queue_name": self.queue.name,
            "job_count": self.queue.count,
            "is_empty": self.queue.is_empty(),
            "connection_status": "connected" if self.redis_conn.ping() else "disconnected"
        }
